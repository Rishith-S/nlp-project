# Gardening Agent

An intelligent gardening assistant that answers your plant care questions using AI and a local database. Ask about symptoms, care routines, watering schedules, or search for expert advice online.

**Features:**
- 🌱 **Smart Query Routing** — Understands whether to answer from local data, search the web, or use both
- 🤖 **LLM-Powered Classification** — Uses AI to classify queries (gardening-related? symptomatic?) for better accuracy
- 🌐 **Live Web Search** — Integrates DuckDuckGo for up-to-date gardening advice when needed
- 💾 **Local SQLite Database** — Stores plant care profiles, personal plant records, and history
- 🎯 **Dual Interface** — Streamlit web UI for interactive use + Jupyter notebook for exploration
- 🛡️ **Safe by Default** — Rejects non-gardening requests and prevents SQL injection

---

## Project Structure

```
nlp-project/
├── agent.py                              # Core routing, classification, and query handling
├── config.py                             # Environment variables, helpers, and utility functions (SQL & web)
├── agent_db.py                           # Database schema and seed data (merged from gardening_agent_seed.py)
├── config.py                             # Environment variables, database paths, helper functions
├── streamlit_app.py                      # Web UI for interactive querying
├── Gardening_Agent_Colab_Notebook_loc.ipynb  # Jupyter notebook for exploration and debugging
├── eval.py                               # Evaluation helpers and demo queries
├── gardening_agent_full_demo.db          # Sample SQLite database (auto-created on first run)
├── requirements.txt                      # Python dependencies
└── README.md                             # This file
```

---

## How It Works

### Query Flow

1. **Input** → User asks a gardening question
2. **Gardening Check** → LLM classifier determines if it's gardening-related
   - ❌ If not → Refusal: "Out of scope"
   - ✓ If yes → Continue
3. **Route Selection** → LLM decides: use **SQL**, **web**, or **both (hybrid)**
   - `sql` — Query local database (e.g., "What plants do I have?")
   - `web` — Search the web (e.g., "How to treat leaf spots?")
   - `hybrid` — Both database and web search
4. **Execute** → Fetch results from chosen source(s)
5. **Compose Answer** → LLM synthesizes results into a clear response

### Key Components

| Module | Purpose |
|--------|---------|
| `agent.py` | **Orchestration**: classifies queries, routes to tools, LLM calls |
| `config.py` | **Utilities & Settings**: env vars, SQL execution, web search (ddgs), and helpers |
| `agent_db.py` | **Data**: SQLite schema, seed data (care profiles + personal plants) |
| `config.py` | **Settings**: env vars, DB paths, date helpers, model initialization |
| `streamlit_app.py` | **UI**: web interface for querying and viewing results |
| `eval.py` | **Testing**: demo queries, benchmarks, security tests |

---

## Setup

### Prerequisites

- Python 3.8+
- OpenRouter API key (for LLM responses)
- Optional: `ddgs` package (for live web search)

### Installation

1. **Clone/Download and navigate to the project:**
   ```powershell
   cd c:\Users\shami\Downloads\nlp-project
   ```

2. **Create a virtual environment:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Install optional web search (recommended):**
   ```powershell
   pip install ddgs
   ```

---

## Configuration

### Required: OpenRouter API Key

This project uses OpenRouter for LLM responses. Set your API key:

```powershell
# PowerShell
$env:OPENROUTER_API_KEY = "sk-your-key-here"

# Or add to .env file (if using python-dotenv)
# OPENROUTER_API_KEY=sk-your-key-here
```

**Models used:**
- **Large model** (default): `meta-llama/llama-3.1-8b-instruct` — Better reasoning, slower
- **Small model** (fallback): `microsoft/phi-3.5-mini-instruct` — Faster, lighter

### Optional: Database Path

Default location is `gardening_agent_full_demo.db` in the project root. To change:

```powershell
$env:DB_PATH = "C:\path\to\custom.db"
```

### Optional: Offline Mode

To run without any external API calls (uses cached responses only):

```powershell
$env:OFFLINE_ONLY = "1"
```

---

## Usage

### Quick Start: Streamlit UI

```powershell
streamlit run streamlit_app.py
```

Then open http://localhost:8501 in your browser. Type your gardening question and get a response.

### Interactive: Jupyter Notebook

```powershell
jupyter notebook Gardening_Agent_Colab_Notebook_loc.ipynb
```

Run cells top to bottom:
1. **Imports** — Load all modules
2. **Database Setup** — Create/seed database
3. **Tool Registration** — Initialize SQL and web search
4. **Demo Queries** — Test the agent with sample questions
5. **Evaluation** — Run security tests, benchmarks, model comparisons

### Direct Python Usage

```python
from agent import handle_query

# Ask a question
result = handle_query("My tomato leaves are yellow with brown spots", model_choice='large')

print(result['final_answer'])      # AI-composed answer
print(result['route'])              # Which tool was used: sql, web, or hybrid
print(result['sources'])            # Where data came from
```

---

## Database

### Schema Overview

The SQLite database contains 4 tables:

| Table | Purpose | Rows |
|-------|---------|------|
| `care_profiles` | Plant care guidelines (humidity, light, watering, pH) | 10 predefined plants |
| `personal_plants` | User's garden inventory (location, status, last watered/fertilized) | 11 sample plants |
| `plant_search_history` | Logged searches (for analytics) | Auto-populated |
| `shopping_list` | User's shopping list (only writable table) | Editable |

### Seed Data

The database is pre-populated with:
- **Care Profiles**: Banana, Cherry Tomatoes, Hibiscus, Succulents, Basil, Mint, Monstera, Snake Plant, Rose, ZZ Plant
- **Personal Plants**: 11 example plants with status (active, monitor, sick, inactive)

To rebuild the database:

```python
from agent_db import reset_database, setup_database

reset_database()  # Drops all tables
setup_database()  # Recreates and seeds
```

---

## Models & Performance

### Model Selection

- **Large model** (Llama 3.1 8B): Recommended for complex queries, better reasoning
- **Small model** (Phi 3.5 Mini): Faster fallback, lower latency, less detailed

The agent tries the selected model first; if it fails or times out, it falls back to the other.

### Typical Latencies

- SQL query: ~0.5–1s
- Web search: ~2–5s (network dependent)
- LLM response: ~1–3s

---

## Security

### Built-in Safeguards

1. **Gardening Scope** — LLM classifier rejects non-gardening queries (e.g., "Tell me a joke")
2. **SQL Injection Prevention** — Parameterized queries for all SQL operations
3. **Write Restrictions** — Only `shopping_list` table is writable; all other tables are read-only
4. **Safe Prompting** — No user input is directly injected into system prompts

### What Gets Logged

- User queries and responses
- Tool usage (SQL, web, hybrid)
- Model performance metrics (latency, success/failure)

---

## Troubleshooting

### "Could not find module agent_db" or import errors

- Ensure you're running from the project root directory
- Check that `.venv` is activated: `.\.venv\Scripts\Activate.ps1`
- Reinstall: `pip install -r requirements.txt`

### Web search not working ("No results from ddgs")

- Install `ddgs`: `pip install ddgs`
- Check internet connection
- Try a simpler search term (avoid special characters)

### Streamlit crashes or slow responses

- Restart Streamlit: `streamlit run streamlit_app.py --logger.level=debug`
- Check that OpenRouter API key is set: `echo $env:OPENROUTER_API_KEY`
- Try the small model for faster responses

### Model responses are empty or templated

- Verify OpenRouter key is valid (check OpenRouter dashboard for usage)
- Check network connectivity and firewall
- Try offline mode: `$env:OFFLINE_ONLY = "1"`

### Database errors ("sqlite3.IntegrityError")

- Reset the database: `python -c "from agent_db import reset_database; reset_database(); setup_database()"`
- Check disk space
- Ensure `gardening_agent_full_demo.db` is not locked by another process

---

## Example Queries

Try these questions to see how the agent routes and responds:

| Query | Expected Route | Notes |
|-------|-----------------|-------|
| "What plants do I have?" | `sql` | Uses local database |
| "My tomato leaves are yellow with brown spots" | `web` or `hybrid` | Searches for disease diagnosis |
| "How often should I water my mint?" | `sql` + `web` | Local profile + expert advice |
| "Tell me a joke" | `refusal` | Out of scope |
| "What's the best rose variety for my climate?" | `web` | Requires current advice |
| "Show me my shopping list" | `sql` | Local table query |

---

## Development & Testing

### Run Evaluation Suite

```python
from eval import run_security_tests, run_benchmarks, run_demo_queries

# Test security (injection, harmful queries)
security_results = run_security_tests()

# Benchmark model performance
benchmarks = run_benchmarks()

# Run 20 demo queries
demo_results = run_demo_queries()
```

### Debug Mode

Enable debug output:

```powershell
$env:DEBUG = "1"
python agent.py  # or streamlit run streamlit_app.py
```

---

## Architecture Decisions

### Why LLM-based Routing?

Previous keyword-based routing was brittle (e.g., "leaves are yellow" ≠ "yellow leaves" as patterns). LLM classification handles natural language variation and nuance better.

### Why Three Models?

- Gardening check + route selection + answer composition each use the best-fit model
- Large model for complex reasoning; small for speed when deterministic
- Fallback ensures robustness if one model fails

### Why Local SQLite?

- Fast queries (no network latency)
- Full control over schema and data
- Easy to seed with example data
- No external dependencies for basic functionality

---

## Future Enhancements

- [ ] Photo recognition for plant identification and symptom diagnosis
- [ ] Historical trend analysis (plant health over time)
- [ ] Seasonal care reminders
- [ ] Integration with weather APIs for watering recommendations
- [ ] Multi-language support

---

## License & Attribution

This project uses:
- **OpenRouter** for LLM inference
- **DuckDuckGo Search** (`ddgs`) for web results
- **SQLite** for data storage
- **Streamlit** for the web interface

See `requirements.txt` for all dependencies.

---

## Questions?

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) above
2. Review the notebook: `Gardening_Agent_Colab_Notebook_loc.ipynb`
3. Inspect logs: `streamlit run streamlit_app.py --logger.level=debug`
