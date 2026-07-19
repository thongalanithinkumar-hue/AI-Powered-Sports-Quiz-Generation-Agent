
## Project Overview

The dashboard lets a user choose a sport and difficulty level, generate a quiz, answer multiple-choice questions, submit responses, and review their score with grounded explanations. The generation pipeline is designed to reduce hallucinations by requiring every question, answer, and explanation to be based only on retrieved context.

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
the published link is `https://ai-powered-sports-quiz-generation-agent-hvw5wwqmwj85ubdzfphxfq.streamlit.app/`
