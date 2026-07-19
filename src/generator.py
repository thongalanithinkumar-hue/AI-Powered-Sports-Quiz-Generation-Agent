import json
import re
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI
from src.database import query_facts_by_sport, get_chroma_client
from src.search import search_recent_news


def _normalize_question(text):
    """Normalize question text for repeat detection."""
    return re.sub(r"\s+", " ", text.strip().lower())


def _is_similar_question(left, right, threshold=0.75):
    """Return True when two questions share most of their meaningful words."""
    left_words = set(re.findall(r"[a-z0-9]+", left.lower()))
    right_words = set(re.findall(r"[a-z0-9]+", right.lower()))
    if not left_words or not right_words:
        return False

    overlap = len(left_words & right_words)
    smaller_question_size = min(len(left_words), len(right_words))
    return overlap / smaller_question_size >= threshold


def _validate_quiz_payload(quiz_data, avoid_questions=None):
    """Validate the minimum quiz shape expected by the Streamlit dashboard."""
    if not isinstance(quiz_data, dict):
        raise ValueError("The model response was not a JSON object.")

    if not quiz_data.get("sport"):
        raise ValueError("The model response is missing the sport name.")
    if not quiz_data.get("difficulty"):
        raise ValueError("The model response is missing the difficulty level.")

    questions = quiz_data.get("questions")
    if not isinstance(questions, list) or not 4 <= len(questions) <= 5:
        raise ValueError("The model response must include 4 to 5 quiz questions.")

    seen_questions = []
    for idx, question in enumerate(questions, 1):
        options = question.get("options")
        correct_answer = question.get("correct_answer")
        question_text = question.get("question", "")
        normalized_question = _normalize_question(question_text)

        if not question_text or not isinstance(options, dict):
            raise ValueError(f"Question {idx} is missing question text or options.")
        if not question.get("explanation"):
            raise ValueError(f"Question {idx} is missing a short explanation.")
        if normalized_question in seen_questions:
            raise ValueError(f"Question {idx} repeats another question in this quiz.")
        if sorted(options.keys()) != ["A", "B", "C", "D"]:
            raise ValueError(f"Question {idx} must include exactly options A, B, C, and D.")
        if correct_answer not in options:
            raise ValueError(f"Question {idx} has an invalid correct_answer value.")

        seen_questions.append(normalized_question)

    return quiz_data


def generate_quiz(sport, difficulty, api_key, avoid_questions=None):
    """
    1. Query ChromaDB for facts about the selected sport.
    2. Search DuckDuckGo for recent news.
    3. Merge context blocks.
    4. Compile system and user prompts instructing the LLM to use ONLY the context.
    5. Query OpenAI using JSON mode.
    6. Return the decoded quiz dictionary.
    """
    # 1. Fetch ChromaDB facts and live search context in parallel.
    client = get_chroma_client()
    retrieval_query = f"{difficulty} {sport} records recent achievements key facts quiz"

    executor = ThreadPoolExecutor(max_workers=2)
    db_future = executor.submit(
        query_facts_by_sport,
        client,
        api_key,
        sport,
        retrieval_query,
        3,
    )
    search_future = executor.submit(search_recent_news, sport)

    db_facts = db_future.result()
    try:
        live_context = search_future.result(timeout=1.25)
    except TimeoutError:
        live_context = (
            f"Fallback Context: Web search timed out for {sport}. "
            "Grounding will rely strictly on database facts."
        )
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    db_context = "\n".join([f"- {fact}" for fact in db_facts]) if db_facts else "No offline database facts available."
    
    # 2. Merge contexts
    request_seed = uuid.uuid4().hex[:8]
    merged_context = (
        f"=== OFFLINE DATABASE KNOWLEDGE ===\n{db_context}\n\n"
        f"=== LIVE SEARCH NEWS ===\n{live_context}"
    )
    
    # 4. Initialize OpenAI client pointing to Groq's API endpoint
    openai_client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
        max_retries=0,
        timeout=12.0,
    )
    
    previous_question_context = ""
    if avoid_questions:
        previous_questions = "\n".join(f"- {question}" for question in avoid_questions[-20:])
        previous_question_context = (
            "PREVIOUS QUESTIONS TO AVOID:\n"
            f"{previous_questions}\n\n"
            "Do not repeat or closely paraphrase any previous question above.\n\n"
        )

    # 5. Build strict instructions
    system_prompt = (
        "Create a grounded sports multiple-choice quiz. Use ONLY the supplied context. "
        "Do not invent facts. Generate exactly 4 diverse questions for the requested difficulty. "
        "Each question must have options A, B, C, D, one correct_answer letter, and a short explanation. "
        "Avoid repeated or closely paraphrased questions. Return valid JSON only."
    )
    
    user_prompt = (
        f"Sport: {sport}\n"
        f"Difficulty: {difficulty}\n\n"
        f"Freshness seed: {request_seed}\n"
        "Use this seed only to vary wording, ordering, and topic mix. Do not use it as factual context.\n\n"
        f"{previous_question_context}"
        f"CONTEXT:\n{merged_context}\n\n"
        "Generate exactly 4 quiz questions. Do not generate fewer than 4 or more than 4.\n\n"
        "Return this JSON shape:\n"
        "{\n"
        "  \"sport\": \"Sport name\",\n"
        "  \"difficulty\": \"Difficulty level\",\n"
        "  \"questions\": [\n"
        "    {\n"
        "      \"question\": \"Quiz question text?\",\n"
        "      \"options\": {\n"
        "        \"A\": \"Answer option A\",\n"
        "        \"B\": \"Answer option B\",\n"
        "        \"C\": \"Answer option C\",\n"
        "        \"D\": \"Answer option D\"\n"
        "      },\n"
        "      \"correct_answer\": \"A\",\n"
        "      \"explanation\": \"Short explanation of the correct answer grounded only in the context.\"\n"
        "    }\n"
        "  ]\n"
        "}"
    )

    # 6. Call Groq API with JSON Mode
    try:
        response = openai_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.8,
            max_tokens=850,
        )
    except (APIConnectionError, APITimeoutError) as exc:
        raise RuntimeError(
            "Could not connect to Groq. Check your internet connection, VPN/firewall, "
            "and then run the app from your local terminal with the project virtual environment."
        ) from exc
    except APIStatusError as exc:
        raise RuntimeError(
            f"Groq API returned an error ({exc.status_code}). Check your API key, account access, and model availability."
        ) from exc

    # 7. Decode, parse, and validate
    raw_response = response.choices[0].message.content
    quiz_data = json.loads(raw_response)
    return _validate_quiz_payload(quiz_data, avoid_questions=avoid_questions)
