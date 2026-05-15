# Gardening Project

A small gardening data app that answers questions using a local SQLite database and optional live web search. It includes a notebook for exploration and a Streamlit UI for interactive use.

## What's here

- Gardening_Agent_Colab_Notebook.ipynb - notebook with setup, helpers, and demos
- gardening_agent_streamlit_app.py - Streamlit UI that loads helper functions from the notebook
- gardening_agent_full_demo.db - sample SQLite database
- requirements.txt - minimal dependencies

## Quick start (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run gardening_agent_streamlit_app.py
```

## Notebook usage

Open Gardening_Agent_Colab_Notebook.ipynb and run cells top to bottom. The notebook defines the helper functions used by the UI (SQL, web search, and query routing).

## Web search configuration

Live web search requires a provider. If none are configured, the app returns a clear error and does not use mock data.

- Set TAVILY_API_KEY for Tavily search
- Set SERPER_API_KEY for Serper search
- Optional: set ALLOW_DDG_SEARCH=1 and install duckduckgo_search for DuckDuckGo fallback

Example (PowerShell):

```powershell
$env:TAVILY_API_KEY = "your-key"
# or
$env:SERPER_API_KEY = "your-key"
# optional DDG fallback
$env:ALLOW_DDG_SEARCH = "1"
```

## Database notes

- The sample database is gardening_agent_full_demo.db.
- The notebook can recreate the demo database when setup_database() is executed.
- Write operations are limited to the shopping_list table.

## Streamlit UI notes

The UI executes code cells from the notebook at runtime to reuse helper functions. Keep the notebook path in gardening_agent_streamlit_app.py accurate if you move files.
