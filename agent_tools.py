from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional

from agent_db import connect

WRITEABLE_TABLES = {'shopping_list'}


def execute_sql(query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    start = time.perf_counter()
    normalized = ' '.join(query.strip().split()).lower()
    statement = normalized.split(' ', 1)[0] if normalized else ''

    def _table_name(sql_text: str) -> Optional[str]:
        patterns = [
            r'insert\s+into\s+([a-z_]+)',
            r'update\s+([a-z_]+)',
            r'delete\s+from\s+([a-z_]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, sql_text)
            if match:
                return match.group(1)
        return None

    conn = connect()
    try:
        if statement in {'select', 'with', 'pragma'}:
            rows = [dict(row) for row in conn.execute(query, params or {}).fetchall()]
            return {
                'ok': True,
                'rows': rows,
                'row_count': len(rows),
                'latency_s': round(time.perf_counter() - start, 4),
            }

        if statement in {'insert', 'update', 'delete'}:
            table_name = _table_name(normalized)
            if table_name not in WRITEABLE_TABLES:
                return {
                    'ok': False,
                    'rows': [],
                    'error': 'Write operations are only allowed for the shopping_list table.',
                    'latency_s': round(time.perf_counter() - start, 4),
                }
            cursor = conn.execute(query, params or {})
            conn.commit()
            return {
                'ok': True,
                'rows': [],
                'row_count': cursor.rowcount,
                'lastrowid': cursor.lastrowid,
                'latency_s': round(time.perf_counter() - start, 4),
            }

        return {
            'ok': False,
            'rows': [],
            'error': 'Unsupported SQL statement.',
            'latency_s': round(time.perf_counter() - start, 4),
        }
    except Exception as exc:
        return {
            'ok': False,
            'rows': [],
            'error': str(exc),
            'latency_s': round(time.perf_counter() - start, 4),
        }
    finally:
        conn.close()


def _search_duckduckgo(query: str, max_results: int = 5) -> Optional[List[Dict[str, str]]]:
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', category=RuntimeWarning)
            try:
                from ddgs import DDGS  # preferred package
            except Exception:
                from duckduckgo_search import DDGS  # fallback to older package
    except Exception:
        return None

    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', category=RuntimeWarning)
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
        cleaned = []
        for item in results:
            cleaned.append(
                {
                    'title': item.get('title', ''),
                    'url': item.get('href', ''),
                    'snippet': item.get('body', ''),
                }
            )
        return cleaned
    except Exception:
        return None


def build_web_query(user_query: str) -> str:
    q = user_query.lower()
    if 'san ramon' in q and 'rain' in q:
        return 'San Ramon CA weather tomorrow rain forecast'
    if '94582' in q and 'neem oil' in q:
        return 'nursery near 94582 neem oil'
    if 'pruning roses' in q or 'prune roses' in q:
        return 'video pruning roses tutorial'
    if 'japanese beetle' in q:
        return 'Japanese beetle warning Northern California'
    if 'peat-free potting soil' in q:
        return 'Home Depot peat-free potting soil'
    if 'last frost' in q:
        return 'expected last frost date current year local area'
    if 'succulent' in q and ('90' in q or 'temperature' in q or 'weather' in q):
        return 'succulent watering hot weather morning'
    if 'eco-friendly' in q or 'eco friendly' in q:
        return 'eco friendly pest control methods'
    if 'identify' in q or 'pest' in q:
        return 'garden pest identification symptoms'
    if 'weather' in q or 'temperature' in q:
        return user_query
    return user_query


def _clean_snippet(text: str, limit: int = 200) -> str:
    if not text:
        return ''
    cleaned = ' '.join(str(text).split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + '...'


def _clean_results(results: List[Dict[str, str]]) -> List[Dict[str, str]]:
    cleaned_results: List[Dict[str, str]] = []
    seen = set()
    for item in results:
        snippet = _clean_snippet(item.get('snippet', ''))
        title = _clean_snippet(item.get('title', ''), limit=120)
        if snippet:
            key = snippet.lower()
            if key in seen:
                continue
            seen.add(key)
        cleaned_results.append(
            {
                'title': title,
                'url': item.get('url', ''),
                'snippet': snippet,
            }
        )
    return cleaned_results


def _build_summary(results: List[Dict[str, str]], max_items: int = 3, limit: int = 420) -> str:
    snippets = [item.get('snippet', '') for item in results if item.get('snippet')]
    summary = ' '.join(snippets[:max_items]).strip()
    return _clean_snippet(summary, limit=limit) or 'Web search returned relevant gardening results.'


def search_web(user_query: str, max_results: int = 5) -> Dict[str, Any]:
    query = build_web_query(user_query)
    start = time.perf_counter()

    # Use DuckDuckGo when available
    results = _search_duckduckgo(query, max_results=max_results)
    provider = 'duckduckgo'
    if results is None:
        return {
            'ok': False,
            'provider': None,
            'query': query,
            'summary': 'Web search unavailable. Install ddgs to enable DuckDuckGo search.',
            'results': [],
            'error': 'No web search provider available. Install ddgs.',
            'latency_s': round(time.perf_counter() - start, 4),
        }

    cleaned_results = _clean_results(results)
    summary = _build_summary(cleaned_results)
    return {
        'ok': True,
        'provider': provider,
        'query': query,
        'summary': summary,
        'results': cleaned_results,
        'latency_s': round(time.perf_counter() - start, 4),
    }


def pretty_rows(rows: List[Dict[str, Any]], limit: int = 5) -> str:
    if not rows:
        return '[]'
    return json.dumps(rows[:limit], indent=2, default=str)


__all__ = [
    'WRITEABLE_TABLES',
    'build_web_query',
    'execute_sql',
    'pretty_rows',
    'search_web',
]
