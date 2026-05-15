# Gardening Project

A small gardening data app that answers questions using a local SQLite database and optional live web search. It includes a notebook for exploration and a Streamlit UI for interactive use.

## What's here

- Gardening_Agent_Colab_Notebook.ipynb - notebook with setup, helpers, and demos
- streamlit_app.py - Streamlit UI for interactive use
- gardening_agent_full_demo.db - sample SQLite database
- requirements.txt - minimal dependencies

## Quick start (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Notebook usage

Open Gardening_Agent_Colab_Notebook.ipynb and run cells top to bottom. The notebook defines the helper functions used by the UI (SQL, web search, and query routing).

## Web search configuration

Live web search requires a provider. If none are configured, the app returns a clear error and does not use mock data.

- Set TAVILY_API_KEY for Tavily search
- Set SERPER_API_KEY for Serper search
- DuckDuckGo uses `duckduckgo_search` (DDGS). Set ALLOW_DDG_SEARCH=1 to enable it as a fallback.

Example (PowerShell):

```powershell
$env:TAVILY_API_KEY = "your-key"
# or
$env:SERPER_API_KEY = "your-key"
# DDGS fallback
$env:ALLOW_DDG_SEARCH = "1"
```

## Model configuration

If you want to use the remote model, set:

```powershell
$env:OPENROUTER_API_KEY = "your-key"
```

To use local models, set:

```powershell
$env:LOCAL_LARGE_MODEL_PATH = "C:\path\to\your\large-model"
$env:LOCAL_SMALL_MODEL_PATH = "C:\path\to\your\small-model"
```

## Database notes

- The sample database is gardening_agent_full_demo.db.
- The notebook can recreate the demo database when setup_database() is executed.
- Write operations are limited to the shopping_list table.

## Streamlit UI notes

The UI imports the helper modules directly (no notebook execution). Keep file names aligned with the imports if you rename modules.
