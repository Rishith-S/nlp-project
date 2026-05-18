# Gardening Agent

This is my LLM-based virtual assistant project for gardening help. The agent answers questions about a small personal garden by combining three things:

- a local SQLite database with plant records, care profiles, logs, expenses, and a shopping list
- live web search for current or outside information, such as weather, nursery/product results, pest alerts, and videos
- two OpenRouter-hosted open-source models so the project can compare a larger and smaller model

The main goal is not to make a fancy app. The goal is to show a useful assistant that knows when to use tools, grounds its answers in tool output, and can be evaluated with a fixed question set.

## What the Agent Can Do

The assistant is built around gardening questions like:

- "What is the watering schedule for my banana plant?"
- "Does my Monstera need repotting based on my logs?"
- "Find a nursery near zip code 94582 selling neem oil."
- "Is it going to rain in San Ramon tomorrow? Should I skip watering?"
- "What are eco-friendly pest control methods?"

For database questions, it reads from SQLite. For current information, it searches the web or calls the weather API. For mixed questions, it combines both.

## How It Works

The app follows a simple pipeline:

1. Check whether the user request is safe and gardening-related.
2. Route the question to one of four paths: `sql`, `web`, `hybrid`, or `direct`.
3. Run the needed tool:
   - SQLite for plant records and logs
   - DuckDuckGo search for web evidence
   - Open-Meteo for San Ramon weather
   - OpenRouter for model responses
4. Build the final answer from the retrieved evidence.
5. Return the answer along with the route, SQL/web details, and model status.

I intentionally made routing mostly deterministic instead of asking the model to classify every request. That made the demo much more reliable, especially for the required evaluation questions.

## Models

The project compares two OpenRouter models:

| Role | Model |
| --- | --- |
| Larger model | `meta-llama/llama-3.3-70b-instruct` |
| Smaller model | `microsoft/phi-3.5-mini-instruct` |

The app can still answer many tool-based questions without a working model key because the database and web answers use grounded templates. The API key is mainly needed for direct model responses and model comparison.

## Project Files

```text
nlp-project/
|-- agent.py                              # Routing, tool orchestration, safety checks, final answers
|-- agent_db.py                           # SQLite schema and seed data
|-- config.py                             # SQL helper, web search, weather lookup, shared config
|-- eval.py                               # Evaluation, benchmarks, cache demo, security tests
|-- streamlit_app.py                      # Minimal UI for user testing
|-- Gardening_Agent_Colab_Notebook_loc.ipynb # Colab/Jupyter notebook for running the full demo
|-- question_dataset.csv                  # 20 planned user queries and expected routes
|-- gardening_agent_full_demo.db          # Seeded SQLite database
|-- requirements.txt
`-- README.md
```

## Database

The SQLite database is seeded from `agent_db.py`. It includes:

- care profiles for plants such as Banana Plant, Cherry Tomatoes, Hibiscus, Succulents, Basil, Mint, Monstera, Snake Plant, Rose, and ZZ Plant
- personal plant records, including location, status, watering intervals, and recent care dates
- watering schedules
- soil readings
- fertilizer history
- repotting records
- growth logs
- expenses and purchase logs
- diagnostics
- a writable shopping list

Only the `shopping_list` table is writable from the assistant. Other tables are read-only for safety.

## Question Dataset

The file `question_dataset.csv` contains the 20 planned project questions. Each row includes:

- the user query
- expected route
- primary tool
- category
- notes

This makes the demo easier to grade because the evaluator can see exactly which questions were planned and how each one is supposed to be handled.

## Setup

I built and tested this with Python 3.11, but the code should work on recent Python 3 versions.

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Seed or reset the database:

```bash
python - <<'PY'
from agent_db import setup_database
setup_database()
PY
```

## OpenRouter Key

Create a `.env` file in the project folder:

```bash
OPENROUTER_API_KEY="your-openrouter-key-here"
```

Or export it in the terminal:

```bash
export OPENROUTER_API_KEY="your-openrouter-key-here"
```

Do not commit the `.env` file. It is already ignored by `.gitignore`.

## Run the Streamlit App

```bash
streamlit run streamlit_app.py
```

Then open:

```text
http://localhost:8501
```

The Streamlit UI shows the full answer, the selected route, model status, SQL rows, and web sources. Search snippets are available in an expander so the page does not look like a raw search dump.

## Run the Notebook

Open the notebook:

```bash
jupyter notebook Gardening_Agent_Colab_Notebook_loc.ipynb
```

If you are running locally and do not already have Jupyter installed, install it first:

```bash
pip install notebook
```

The notebook is meant for grading and walkthroughs. It runs setup, example queries, prompt technique demos, caching, security tests, and model comparisons. The answer tables are configured to show full answers instead of shortened previews.

## Use From Python

```python
from agent import handle_query

result = handle_query(
    "Is it going to rain in San Ramon tomorrow? Should I skip watering?",
    model_choice="large",
)

print(result["route"])
print(result["final_answer"])
print(result["web_result"])
```

## Evaluation

Run the main project checks:

```python
from eval import run_demo_queries, run_benchmarks, run_security_tests

demo_results = run_demo_queries(model_choice="large")
benchmarks = run_benchmarks()
security_results = run_security_tests()
```

The evaluation covers:

- route accuracy on the 20-question dataset
- large vs small model comparison
- prompt caching demo
- prompting technique examples
- prompt-injection/security tests
- SQL write safety checks

## Prompting Techniques

The project includes examples for:

- baseline prompting
- prompt chaining
- meta prompting
- self-reflection prompting

These are implemented in `run_prompting_techniques()` in `eval.py`.

## Security Testing

The assistant refuses requests that try to:

- reveal API keys or hidden prompts
- override system/developer instructions
- perform prompt injection
- run dangerous SQL
- ask non-gardening questions

SQL writes are restricted to the shopping list, and generated SQL uses parameters where user-provided values are involved.

## Current Limitations

This is still a course project, so there are a few honest limitations:

- Web search quality can vary because DuckDuckGo results change.
- Live product availability is not guaranteed, so the agent tells users to call or verify before buying.
- Weather answers are centered on San Ramon because that is the demo location.
- The database is a small seeded dataset, not a real user account system.
- The UI is intentionally simple because the focus is tool use and evaluation.

## Tech Stack

- Python
- SQLite
- Streamlit
- pandas
- DuckDuckGo search through `ddgs`, with an HTML fallback
- Open-Meteo weather API
- OpenRouter for model calls
