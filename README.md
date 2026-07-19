# AI-Powered Sports Quiz Agent

An interactive Streamlit dashboard that generates sports quizzes using retrieval-augmented generation. The app combines a local ChromaDB knowledge base with live DuckDuckGo web search snippets, then sends the grounded context to a Groq-hosted LLM through the OpenAI-compatible SDK.

## Project Overview

The dashboard lets a user choose a sport and difficulty level, generate a quiz, answer multiple-choice questions, submit responses, and review their score with grounded explanations. The generation pipeline is designed to reduce hallucinations by requiring every question, answer, and explanation to be based only on retrieved context.

## Key Features

- AI-powered quiz generation using the OpenAI SDK with Groq's OpenAI-compatible endpoint.
- ChromaDB retrieval from a local sports facts dataset using deterministic local embeddings.
- Live web search integration through DuckDuckGo Search for current sports information when available.
- Difficulty-aware prompt construction for Easy, Medium, and Hard quizzes.
- Interactive Streamlit dashboard with answer selection, scoring, feedback, and regeneration.
- Guardrails for malformed model responses before rendering quiz data.
- Fresh quiz variation on each request while keeping all questions grounded in retrieved context.
- Lazy loading keeps the dashboard startup fast; ChromaDB and LLM modules load only when a quiz is generated.

## Architecture

```text
sports-quiz-agent/
|-- app.py                  Streamlit dashboard and session state
|-- requirements.txt        Python dependencies
|-- .env.example            Environment variable template
|-- data/
|   |-- sports_facts.json   Offline sports knowledge base
|-- src/
|   |-- config.py           Environment loading
|   |-- database.py         ChromaDB setup, population, and retrieval
|   |-- search.py           DuckDuckGo web search helper
|   |-- generator.py        Context assembly, prompting, LLM call, validation
```

## How It Works

1. The app loads `GROQ_API_KEY` from `.env` or the system environment.
2. The dashboard starts quickly and waits to initialize ChromaDB until the first quiz request.
3. ChromaDB is initialized as a persistent local database in `chroma_db/`.
4. Facts from `data/sports_facts.json` are inserted into the `sports_facts_local` collection on first run.
5. When a quiz is requested, the app retrieves sport-specific facts from ChromaDB and ranks them for relevance.
6. DuckDuckGo Search fetches recent context and source URLs for the selected sport when available.
7. The retrieved facts and search snippets are merged into a single grounded context.
8. The LLM generates a fresh JSON quiz with questions, options, correct answers, and explanations.
9. The dashboard renders the quiz and calculates the user's score after submission.

## Quiz Output Format

Each generated quiz includes:

- Sport name.
- Difficulty level.
- Four quiz questions.
- Four answer options per question: `A`, `B`, `C`, and `D`.
- Correct answer key for every question.
- Short explanation for every correct answer.

## Setup Instructions

### 1. Prerequisites

Install Python 3.10 or newer.

### 2. Create a Virtual Environment

From the project folder:

```powershell
cd "C:\Users\thong\OneDrive\Desktop\Project\sports-quiz-agent"
python -m venv venv
```

Activate it on Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

If activation is blocked by your execution policy, you can run commands directly through the venv Python:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure API Key

Create a `.env` file from the example:

```powershell
Copy-Item .env.example .env
```

Edit `.env`:

```env
GROQ_API_KEY=your_groq_api_key_here
```

The API key is intentionally not shown in the Streamlit interface.

### 5. Run the Dashboard

```powershell
streamlit run app.py
```

Or, without activating the environment:

```powershell
.\venv\Scripts\python.exe -m streamlit run app.py
```

The app will open at the local Streamlit URL, usually `http://localhost:8501`.

## Evaluation Criteria Mapping

- Accuracy of generated quizzes: prompts require all quiz content to be grounded in retrieved context, and the response shape is validated before display.
- Quality and relevance of retrieved information: ChromaDB retrieval is filtered by sport, ranked against the quiz query, and combined with recent DuckDuckGo search snippets and source URLs.
- Effective use of the AI agent: the LLM receives structured context, difficulty settings, and strict JSON output instructions.
- Correct ChromaDB implementation: `src/database.py` creates a persistent collection, populates it idempotently, embeds facts locally, and queries with metadata filters.
- User experience and usability: the dashboard supports sport selection, difficulty selection, clean answer selection, scoring, explanations, regeneration, and quiz clearing.
- Code quality and documentation: the app is split into focused modules with setup instructions and project overview in this README.
- Freshness and diversity: each generation request includes a variation seed and prompt rules to vary wording, topic mix, option order, and explanations.

## Notes

- `chroma_db/` is generated automatically and should not be committed.
- DuckDuckGo results may vary by time and availability. If search fails, the app falls back to local ChromaDB facts.
- The app uses a lightweight local embedding function for ChromaDB, so it does not need to download an embedding model on first run.
- The app generates exactly four questions for faster and more reliable responses while satisfying the assignment requirement of four to five questions.
