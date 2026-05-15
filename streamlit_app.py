import json
import pathlib
import time
import streamlit as st
from typing import Any, Dict

NB_PATH = pathlib.Path(__file__).parent / "Gardening_Agent_Colab_Notebook.ipynb"


@st.cache_resource(show_spinner=False)
def load_notebook_namespace(nb_path: pathlib.Path) -> Dict[str, Any]:
    """Load and exec code cells from the notebook into a namespace dict.
    This allows reusing the notebook's helper functions (execute_sql, search_web, handle_query).
    """
    ns: Dict[str, Any] = {}
    # If the notebook file is missing, return a namespaced error for the caller to render
    if not nb_path.exists():
        ns['__load_error__'] = f'Notebook not found: {nb_path}'
        return ns
    raw = json.loads(nb_path.read_text(encoding='utf-8'))
    for cell in raw.get('cells', []):
        if cell.get('cell_type') != 'code':
            continue
        src = ''.join(cell.get('source', []))

        # Heuristic: only execute cells that contain definitions or imports
        # (these cells define functions/classes we need, regardless of size)
        exec_keywords = ('def ', 'class ', 'import ', 'from ', 'async def ', '@')
        has_definitions = any(k in src for k in exec_keywords)

        if not has_definitions:
            # Skip cells that are just running code (demo/benchmark cells)
            ns.setdefault('__skipped_cells__', 0)
            ns['__skipped_cells__'] += 1
            continue

        try:
            exec(compile(src, '<notebook>', 'exec'), ns)
        except Exception as exc:
            # Stop loading further if a cell fails — report to user later
            ns['__load_error__'] = str(exc)
            break
    return ns


def pretty_rows(rows):
    import json
    try:
        return json.dumps(rows, indent=2, default=str)
    except Exception:
        return str(rows)


st.set_page_config(page_title='Gardening Agent Demo', layout='wide')
st.title('Gardening Agent — Live Demo UI')

col1, col2 = st.columns([3, 1])

with col1:
    query = st.text_area('Ask a gardening question', height=140, placeholder='Example: What is the watering schedule for my banana plant?')
    run = st.button('Ask')

with col2:
    st.markdown('**Demo controls**')
    show_ns = st.checkbox('Show loaded functions (debug)', value=False)

status = st.empty()

if run:
    status.text('Loading notebook and helpers...')
    ns = load_notebook_namespace(NB_PATH)
    if '__load_error__' in ns:
        st.error('Failed to load notebook code: ' + ns['__load_error__'])
    else:
        if show_ns:
            st.write('Loaded symbols:', sorted(k for k in ns.keys() if not k.startswith('__')))

        # If the notebook defines a handle_query, prefer it
        handle_query = ns.get('handle_query')
        search_web = ns.get('search_web')
        execute_sql = ns.get('execute_sql')

        if handle_query is None:
            st.error('Notebook did not expose handle_query(); cannot process queries.')
        else:
            start = time.perf_counter()
            try:
                response = handle_query(query)
            except Exception as exc:
                st.exception(exc)
                response = None
            elapsed = round(time.perf_counter() - start, 3)

            if response is None:
                status.text('Query failed.')
            else:
                st.success(f"Answered in {elapsed}s — route: {response.get('route')}")
                st.subheader('Final Answer')
                st.write(response.get('final_answer'))

                st.subheader('Details')
                st.markdown('**SQL Query**')
                st.code(response.get('sql_query') or '—')

                st.markdown('**SQL Result (first rows)**')
                sql_result = response.get('sql_result') or {}
                rows = sql_result.get('rows') if isinstance(sql_result, dict) else None
                if rows:
                    st.text(pretty_rows(rows[:10]))
                else:
                    st.write('No SQL rows')

                st.markdown('**Web Result**')
                web = response.get('web_result') or {}
                if web.get('ok'):
                    st.write(web.get('summary'))
                    st.write(web.get('results', [])[:5])
                else:
                    st.write('No web results or web search unavailable.')

                st.markdown('**Write result (if any)**')
                st.write(response.get('write_result') or '—')

status.text('Ready')

st.sidebar.markdown('---')
st.sidebar.markdown('Gardening Agent Streamlit UI — wraps the notebook functions.')
st.sidebar.markdown('Database: gardening_agent_full_demo.db')
