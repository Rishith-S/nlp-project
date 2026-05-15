Gardening Agent Streamlit UI

Files:
- gardening_agent_streamlit_app.py — Streamlit app that loads and reuses the notebook's helper functions.
- requirements.txt — minimal requirements.

Run locally (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run gardening_agent_streamlit_app.py
```

Notes:
- The app loads `c:/Users/shami/Downloads/nlp-project/Gardening_Agent_Colab_Notebook.ipynb` at runtime and executes its code cells to reuse `handle_query()` and related helpers. Keep the notebook path correct.
- Tavily/Serper keys: the notebook already contains `TAVILY_API_KEY` embedded; to prefer environment variables, set `TAVILY_API_KEY` and/or `SERPER_API_KEY` in your shell before running.
- The app will recreate the demo DB if the notebook's `setup_database()` is executed by the notebook code. If you want to preserve your DB, edit the notebook to skip `setup_database()` on import.

EE submission notes:
- The notebook includes an EE section with prompting techniques, prompt caching, model distillation, and security tests.
- Run all notebook cells top to bottom before export to ensure outputs are included.
- Export a PDF from VS Code (Notebook: Export > PDF) after execution.
- Zip the notebook plus this README and requirements.txt for submission.
