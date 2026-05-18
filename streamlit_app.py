import os
import time
import streamlit as st

from agent import handle_query
from config import pretty_rows


st.set_page_config(page_title='Gardening Agent Demo', layout='wide')
st.title('Gardening Agent — Live Demo UI')

col1, col2 = st.columns([3, 1])

with col1:
    query = st.text_area('Ask a gardening question', height=140, placeholder='Example: What is the watering schedule for my banana plant?')
    run = st.button('Ask')

with col2:
    st.markdown('**Demo controls**')

status = st.empty()

if run:
    status.text('Running query...')
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
        final_answer = response.get('final_answer') or ''
        st.markdown(final_answer)
        with st.expander('Full answer text'):
            st.text_area('Full answer', value=final_answer, height=220, label_visibility='collapsed')

        st.subheader('Details')
        model_error = response.get('model_error')
        if model_error:
            st.markdown('**Model Status**')
            st.warning(model_error)

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
            st.caption(f"Provider: {web.get('provider', 'unknown')} · Query: {web.get('query', '—')}")
            st.write(web.get('summary'))
            results = web.get('results', [])[:5]
            if results:
                for idx, item in enumerate(results, start=1):
                    title = item.get('title') or 'Source'
                    url = item.get('url') or ''
                    if url:
                        st.markdown(f"{idx}. [{title}]({url})")
                    else:
                        st.markdown(f"{idx}. {title}")
                with st.expander('Search snippets'):
                    for idx, item in enumerate(results, start=1):
                        snippet = item.get('snippet') or ''
                        if snippet:
                            st.caption(f"{idx}. {snippet}")
        else:
            st.write('No web results or web search unavailable.')

        st.markdown('**Write result (if any)**')
        st.write(response.get('write_result') or '—')

status.text('Ready')

st.sidebar.markdown('---')
st.sidebar.markdown(
    f"OpenRouter key visible: **{'yes' if os.getenv('OPENROUTER_API_KEY') else 'no'}**"
)
st.sidebar.markdown('Gardening Agent Streamlit UI — wraps the notebook functions.')
st.sidebar.markdown('Database: gardening_agent_full_demo.db')
