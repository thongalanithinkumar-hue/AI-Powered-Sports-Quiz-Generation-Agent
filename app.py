import os
import sys

import streamlit as st

# Add project directory to sys.path to allow imports from src.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config import get_api_key


st.set_page_config(
    page_title="AI Sports Quiz Agent",
    page_icon="🏆",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main-title {
        background: linear-gradient(135deg, #0f172a, #1e293b);
        color: white;
        padding: 24px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 25px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .main-title h1 {
        color: white !important;
        margin: 0;
        font-weight: 800;
        font-size: 2.2rem;
        letter-spacing: 0;
    }
    .main-title p {
        margin: 8px 0 0 0;
        opacity: 0.85;
        font-size: 1.05rem;
        font-weight: 300;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="main-title">
        <h1>AI Sports Quiz Agent</h1>
        <p>Fact-grounded sports trivia powered by ChromaDB retrieval and live web search.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def reset_quiz_state():
    """Clear quiz answers and submission state before generating a new quiz."""
    st.session_state.answers = {}
    st.session_state.submitted = False
    st.session_state.error = None


def click_generate(sport, difficulty, api_key):
    """Generate a quiz for the selected sport and difficulty."""
    from src.generator import generate_quiz

    reset_quiz_state()
    with st.spinner(f"Generating a {difficulty} {sport} quiz..."):
        try:
            prepare_knowledge_base(api_key)
            history_key = f"{sport}:{difficulty}"
            previous_questions = st.session_state.question_history.get(history_key, [])
            st.session_state.quiz = generate_quiz(
                sport,
                difficulty,
                api_key,
                avoid_questions=previous_questions,
            )
            generated_questions = [
                question.get("question", "")
                for question in st.session_state.quiz.get("questions", [])
                if question.get("question")
            ]
            st.session_state.question_history[history_key] = (
                previous_questions + generated_questions
            )[-30:]
        except Exception as exc:
            error_message = str(exc)
            if "connection error" in error_message.lower():
                error_message = (
                    "Could not connect to Groq. Check your internet connection, VPN/firewall, "
                    "and make sure you started the app from the project virtual environment."
                )
            st.session_state.error = error_message
            st.session_state.quiz = None


@st.cache_resource(show_spinner=False)
def prepare_knowledge_base(api_key):
    """Initialize ChromaDB once per app session."""
    from src.database import get_chroma_client, populate_database_if_empty

    client = get_chroma_client()
    populate_database_if_empty(client, api_key)
    return True


env_api_key = get_api_key()
api_key = env_api_key.strip() if env_api_key else ""

if not api_key:
    st.warning(
        "**Groq API Key Required**\n"
        "Add your Groq API key to the `.env` file before generating quizzes."
    )
    st.info("Create an API key on the [Groq Console](https://console.groq.com/).")
    st.stop()

st.sidebar.markdown("### Quiz Customization")

sport = st.sidebar.selectbox(
    "Select Sport",
    ["Cricket", "Football", "Tennis", "Badminton", "Basketball"],
)

difficulty = st.sidebar.selectbox(
    "Select Difficulty",
    ["Easy", "Medium", "Hard"],
)

if "quiz" not in st.session_state:
    st.session_state.quiz = None
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "error" not in st.session_state:
    st.session_state.error = None
if "question_history" not in st.session_state:
    st.session_state.question_history = {}

if st.sidebar.button("Generate New Quiz", type="primary", use_container_width=True):
    click_generate(sport, difficulty, api_key)

if st.session_state.error:
    st.error(f"Quiz generation failed:\n{st.session_state.error}")

if st.session_state.quiz:
    quiz = st.session_state.quiz
    q_list = quiz.get("questions", [])

    st.write(f"### {quiz.get('sport', sport)} Trivia ({quiz.get('difficulty', difficulty)} level)")
    st.write("Questions are grounded in ChromaDB facts plus current DuckDuckGo search snippets.")
    st.write("---")

    for idx, question in enumerate(q_list):
        with st.container(border=True):
            st.markdown(f"##### Question {idx + 1}")
            st.write(question.get("question"))

            options = question.get("options", {})
            option_keys = sorted(options.keys())
            option_labels = [f"{key}) {options[key]}" for key in option_keys]

            previous_choice = st.session_state.answers.get(idx)
            previous_index = option_keys.index(previous_choice) if previous_choice in option_keys else None

            selected_option_label = st.radio(
                f"Options for Q{idx + 1}",
                option_labels,
                index=previous_index,
                key=f"radio_q_{idx}",
                disabled=st.session_state.submitted,
                label_visibility="collapsed",
            )

            selected_key = selected_option_label[0] if selected_option_label else None
            if selected_key:
                st.session_state.answers[idx] = selected_key
            else:
                st.session_state.answers.pop(idx, None)

            if st.session_state.submitted:
                correct = question.get("correct_answer")
                if selected_key == correct:
                    st.success("**Correct!**")
                else:
                    st.error(f"**Incorrect.** The correct answer was **{correct}: {options.get(correct)}**")

                st.info(f"**Explanation:** {question.get('explanation')}")

    st.write("---")

    if not st.session_state.submitted:
        if st.button("Submit Answers", type="primary", use_container_width=True):
            if len(st.session_state.answers) < len(q_list):
                st.warning("Please select an answer for every question before submitting.")
            else:
                st.session_state.submitted = True
                st.rerun()
    else:
        score = sum(
            1
            for idx, question in enumerate(q_list)
            if st.session_state.answers.get(idx) == question.get("correct_answer")
        )
        total = len(q_list)
        pct = int((score / total) * 100) if total > 0 else 0

        st.markdown(f"#### Your Score: **{score} / {total}** ({pct}%)")
        if pct == 100:
            st.balloons()
            st.success("Perfect score. You are a sports expert!")
        elif pct >= 70:
            st.success("Great job. You know your sports well!")
        else:
            st.warning("Keep practicing. Grounded explanations will help you learn.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Regenerate Quiz", use_container_width=True):
                click_generate(sport, difficulty, api_key)
                st.rerun()
        with col2:
            if st.button("Clear Quiz", use_container_width=True):
                st.session_state.quiz = None
                reset_quiz_state()
                st.rerun()
else:
    if not st.session_state.error:
        st.info("Choose a sport and difficulty level, then generate your quiz.")
