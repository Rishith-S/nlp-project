# Gardening Agent

An intelligent gardening assistant that helps users with plant care questions using AI and a local database. Users can ask about plant symptoms, watering schedules, care routines, or search for gardening advice online.

## Features

* Smart query routing using SQL, web search, or both together
* LLM based query classification for better accuracy
* Live web search using DuckDuckGo for recent gardening information
* Local SQLite database for plant care profiles and user plant records
* Streamlit web interface and Jupyter notebook support
* Safety checks to reject non gardening queries and prevent SQL injection

---

# Project Structure

```text
nlp-project/
├── agent.py                              # Core routing, classification, and query handling
├── config.py                             # Environment variables, helper functions, SQL and web utilities
├── agent_db.py                           # Database schema and seed data
├── streamlit_app.py                      # Streamlit web interface
├── Gardening_Agent_Colab_Notebook_loc.ipynb  # Jupyter notebook for testing and exploration
├── eval.py                               # Evaluation and testing scripts
├── gardening_agent_full_demo.db          # SQLite database
├── requirements.txt                      # Python dependencies
└── README.md                             # Project documentation
```

---

# How It Works

## Query Flow

1. User asks a gardening question
2. The system checks if the query is gardening related
3. The assistant decides whether to use:

   * SQL database
   * web search
   * hybrid mode
4. Results are collected from the selected source
5. The LLM generates the final response

### Example Routes

* `sql` → "What plants do I have?"
* `web` → "How to treat leaf spots?"
* `hybrid` → "How often should I water my mint?"

---

# Main Components

| Module             | Purpose                                                        |
| ------------------ | -------------------------------------------------------------- |
| `agent.py`         | Handles routing, query classification, and response generation |
| `config.py`        | Helper functions, environment settings, SQL and web utilities  |
| `agent_db.py`      | Database setup and seed data                                   |
| `streamlit_app.py` | Web interface                                                  |
| `eval.py`          | Security testing and evaluation                                |

---

# Setup

## Requirements

* Python 3.8+
* OpenRouter API key
* Optional: `ddgs` package for web search

## Installation

### 1. Move to the project folder

```powershell
cd c:\Users\shami\Downloads\nlp-project
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Install web search package

```powershell
pip install ddgs
```

---

# Configuration

## OpenRouter API Key

```powershell
$env:OPENROUTER_API_KEY = "sk-your-key-here"
```

### Models Used

* Large model: `meta-llama/llama-3.1-8b-instruct`
* Small model: `microsoft/phi-3.5-mini-instruct`

## Optional Database Path

```powershell
$env:DB_PATH = "C:\path\to\custom.db"
```

## Offline Mode

```powershell
$env:OFFLINE_ONLY = "1"
```

---

# Usage

## Streamlit Interface

```powershell
streamlit run streamlit_app.py
```

Open:

```text
http://localhost:8501
```

## Jupyter Notebook

```powershell
jupyter notebook Gardening_Agent_Colab_Notebook_loc.ipynb
```

## Python Example

```python
from agent import handle_query

result = handle_query(
    "My tomato leaves are yellow with brown spots",
    model_choice='large'
)

print(result['final_answer'])
print(result['route'])
print(result['sources'])
```

---

# Database

## Tables

| Table                  | Purpose                |
| ---------------------- | ---------------------- |
| `care_profiles`        | Plant care information |
| `personal_plants`      | User plant records     |
| `plant_search_history` | Search history         |
| `shopping_list`        | Editable shopping list |

## Sample Data

The database contains sample data for:

* Banana
* Tomato
* Hibiscus
* Succulents
* Basil
* Mint
* Monstera
* Snake Plant
* Rose
* ZZ Plant

---

# Security

## Safety Features

1. Gardening only query checking
2. SQL injection prevention using parameterized queries
3. Limited write access to database tables
4. Safe prompt handling

## Logging

The system logs:

* User queries
* Tool usage
* Model performance metrics

---

# Example Queries

| Query                             | Route             |
| --------------------------------- | ----------------- |
| "What plants do I have?"          | `sql`             |
| "My tomato leaves are yellow"     | `web` or `hybrid` |
| "How often should I water basil?" | `hybrid`          |
| "Tell me a joke"                  | `refusal`         |
| "Show my shopping list"           | `sql`             |

---

# Development and Testing

## Run Evaluation Tests

```python
from eval import run_security_tests
from eval import run_benchmarks
from eval import run_demo_queries

security_results = run_security_tests()
benchmarks = run_benchmarks()
demo_results = run_demo_queries()
```

## Debug Mode

```powershell
$env:DEBUG = "1"
python agent.py
```

---

# Design Decisions

## Why LLM Based Routing?

Keyword based routing was not flexible enough for different ways users ask questions. LLM classification handles natural language better and improves routing accuracy.

## Why SQLite?

SQLite is lightweight, simple to use, and fast for local retrieval tasks.

## Why Multiple Models?

The large model gives better reasoning while the smaller model gives faster responses and works as a fallback.

---

# Future Improvements

* Plant disease image recognition
* Weather API integration
* Seasonal care reminders
* Plant health tracking
* Multi language support

---

# Technologies Used

* OpenRouter
* DuckDuckGo Search (`ddgs`)
* SQLite
* Streamlit
* Python
