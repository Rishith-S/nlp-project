from __future__ import annotations

import json
import os
import re
import sqlite3
import statistics
import textwrap
import time
from html import unescape
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, quote_plus, urlparse
import pandas as pd

try:
    from IPython.display import display
except ImportError:
    display = print

OFFLINE_ONLY = False

DB_PATH = Path('gardening_agent_full_demo.db')
TODAY = date.today()
MONTH_START = TODAY.replace(day=1)
LAST_MONTH_END = MONTH_START - timedelta(days=1)
LAST_MONTH_START = LAST_MONTH_END.replace(day=1)
LAST_MONTH_KEY = LAST_MONTH_START.strftime('%Y-%m')
CURRENT_MONTH_DAY = TODAY - timedelta(days=5)


def _iso(days_ago: int) -> str:
    return (TODAY - timedelta(days=days_ago)).isoformat()


__all__ = [
    'Any',
    'CURRENT_MONTH_DAY',
    'DB_PATH',
    'Dict',
    'LAST_MONTH_END',
    'LAST_MONTH_KEY',
    'LAST_MONTH_START',
    'List',
    'MONTH_START',
    'OFFLINE_ONLY',
    'Optional',
    'Path',
    'TODAY',
    '_iso',
    'dataclass',
    'date',
    'datetime',
    'display',
    'json',
    'os',
    'pd',
    're',
    'sqlite3',
    'statistics',
    'textwrap',
    'time',
    'timedelta',
]


# --- agent_tools merged below ---

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

    # import connect lazily to avoid circular imports with agent_db
    try:
        from agent_db import connect
    except Exception:
        return {
            'ok': False,
            'rows': [],
            'error': 'Database backend unavailable',
            'latency_s': round(time.perf_counter() - start, 4),
        }

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
        try:
            conn.close()
        except Exception:
            pass


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


def _decode_duckduckgo_url(href: str) -> str:
    href = unescape(href)
    if href.startswith('//'):
        href = 'https:' + href
    parsed = urlparse(href)
    if 'duckduckgo.com' in parsed.netloc and parsed.path.startswith('/l/'):
        target = parse_qs(parsed.query).get('uddg', [''])[0]
        return target or href
    return href


def _strip_html(text: str) -> str:
    text = re.sub(r'<.*?>', ' ', text, flags=re.S)
    return ' '.join(unescape(text).split())


def _search_duckduckgo_html(query: str, max_results: int = 5) -> Optional[List[Dict[str, str]]]:
    try:
        import requests
    except Exception:
        return None

    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code >= 400:
            return None
    except Exception:
        return None

    html = response.text
    matches = list(re.finditer(
        r'<a[^>]*class="result__a"[^>]*href="(?P<href>.*?)"[^>]*>(?P<title>.*?)</a>',
        html,
        flags=re.S,
    ))
    results: List[Dict[str, str]] = []
    for idx, match in enumerate(matches[:max_results]):
        next_start = matches[idx + 1].start() if idx + 1 < len(matches) else len(html)
        block = html[match.end():next_start]
        snippet_match = re.search(
            r'class="result__snippet"[^>]*>(?P<snippet>.*?)</a>',
            block,
            flags=re.S,
        )
        results.append(
            {
                'title': _strip_html(match.group('title')),
                'url': _decode_duckduckgo_url(match.group('href')),
                'snippet': _strip_html(snippet_match.group('snippet')) if snippet_match else '',
            }
        )
    return results or None


def _san_ramon_weather(user_query: str) -> Optional[Dict[str, Any]]:
    q = user_query.lower()
    if 'san ramon' not in q or not any(word in q for word in ['rain', 'weather', 'temperature', 'temp', 'forecast']):
        return None
    try:
        import requests
    except Exception:
        return None

    url = (
        'https://api.open-meteo.com/v1/forecast'
        '?latitude=37.7799&longitude=-121.9780'
        '&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum'
        '&temperature_unit=fahrenheit&precipitation_unit=inch'
        '&forecast_days=3&timezone=America%2FLos_Angeles'
    )
    start = time.perf_counter()
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception:
        return None

    daily = data.get('daily', {})
    dates = daily.get('time', [])
    if not dates:
        return None

    target_idx = 1 if 'tomorrow' in q and len(dates) > 1 else 0
    target_date = dates[target_idx]
    rain_chance = daily.get('precipitation_probability_max', [None])[target_idx]
    rain_amount = daily.get('precipitation_sum', [None])[target_idx]
    temp_high = daily.get('temperature_2m_max', [None])[target_idx]
    temp_low = daily.get('temperature_2m_min', [None])[target_idx]

    rain_phrase = (
        f"{rain_chance}% chance of precipitation"
        if rain_chance is not None
        else "precipitation chance unavailable"
    )
    amount_phrase = (
        f"{rain_amount:.2f} in expected"
        if isinstance(rain_amount, (int, float))
        else "precipitation amount unavailable"
    )
    temp_phrase = (
        f"high {temp_high:.0f}F / low {temp_low:.0f}F"
        if isinstance(temp_high, (int, float)) and isinstance(temp_low, (int, float))
        else "temperature unavailable"
    )
    summary = (
        f"San Ramon forecast for {target_date}: {rain_phrase}, {amount_phrase}, {temp_phrase}. "
        "Skip watering if the soil is already moist or if rain is likely; otherwise water based on soil moisture."
    )
    return {
        'ok': True,
        'provider': 'open-meteo',
        'query': 'San Ramon weather forecast',
        'summary': summary,
        'results': [
            {
                'title': 'Open-Meteo San Ramon Forecast',
                'url': 'https://open-meteo.com/',
                'snippet': summary,
            }
        ],
        'weather': {
            'date': target_date,
            'precipitation_probability_max': rain_chance,
            'precipitation_sum_in': rain_amount,
            'temperature_2m_max_f': temp_high,
            'temperature_2m_min_f': temp_low,
        },
        'latency_s': round(time.perf_counter() - start, 4),
    }


def _candidate_web_queries(user_query: str) -> List[str]:
    q = user_query.lower()
    if 'san ramon' in q and 'rain' in q:
        return ['San Ramon CA weather tomorrow rain forecast']
    if '94582' in q and 'neem oil' in q:
        return [
            'neem oil San Ramon 94582 garden center',
            '"neem oil" "San Ramon" "94582"',
            'site:idiggreenacres.com neem oil California garden center',
        ]
    if 'pruning roses' in q or 'prune roses' in q:
        return [
            'video pruning roses tutorial extension master gardener',
            'site:youtube.com pruning roses tutorial',
        ]
    if 'japanese beetle' in q:
        return [
            'site:cdfa.ca.gov Japanese beetle California',
            'site:ipm.ucanr.edu Japanese beetle California eradication',
            'Japanese beetle warning Northern California',
        ]
    if 'peat-free potting soil' in q:
        return [
            'Home Depot peat-free potting soil PittMoss',
            'peat-free potting soil buy California',
        ]
    if 'last frost' in q:
        return [
            'San Ramon CA 94582 last frost date planting calendar',
            '94582 last frost date garden planting calendar',
        ]
    if 'succulent' in q and ('90' in q or 'temperature' in q or 'weather' in q):
        return [
            'succulent watering hot weather morning extension',
            'succulent watering heat wave soil dry morning',
        ]
    if 'eco-friendly' in q or 'eco friendly' in q:
        return [
            'site:edu garden integrated pest management insecticidal soap neem oil extension',
            'university extension integrated pest management garden pest control insecticidal soap neem oil',
        ]
    if 'identify' in q or 'pest' in q:
        return ['garden pest identification symptoms extension']
    if 'weather' in q or 'temperature' in q:
        return [user_query]
    return [user_query]


def build_web_query(user_query: str) -> str:
    return _candidate_web_queries(user_query)[0]


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
        url = item.get('url', '')
        key = (url or title or snippet).lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned_results.append(
            {
                'title': title,
                'url': url,
                'snippet': snippet,
            }
        )
    return cleaned_results


def _source_score(item: Dict[str, str], user_query: str) -> int:
    q = user_query.lower()
    title = item.get('title', '').lower()
    url = item.get('url', '').lower()
    snippet = item.get('snippet', '').lower()
    text = f"{title} {url} {snippet}"
    score = 0

    trusted_markers = [
        '.edu',
        '.gov',
        'extension',
        'ucanr.edu',
        'ipm.ucanr.edu',
        'cdfa.ca.gov',
        'hgic.clemson.edu',
        'colostate.edu',
        'extension.unr.edu',
        'gardeningsolutions.ifas.ufl.edu',
        'almanac.com',
        'garden.org',
        'homedepot.com',
        'devilmountainnursery.com',
        'idiggreenacres.com',
        'manta.com',
        'alignable.com',
        'youtube.com',
    ]
    weak_markers = [
        'facebook.com',
        'pinterest.',
        'wikipedia.org',
        'yelp.com',
        'amazon.com',
        'reddit.com',
        'quora.com',
    ]
    for marker in trusted_markers:
        if marker in url:
            score += 8
    for marker in weak_markers:
        if marker in url:
            score -= 8

    for word in re.findall(r'[a-z0-9]+', q):
        if len(word) > 3 and word in text:
            score += 1

    if '94582' in q and 'neem oil' in q:
        if 'neem' not in text:
            score -= 50
        for marker in ['neem oil', 'san ramon', '94582', 'devil mountain', 'organeem', 'garden center', 'nursery']:
            if marker in text:
                score += 7
    if 'eco-friendly' in q or 'eco friendly' in q:
        for marker in ['integrated pest management', 'insecticidal soap', 'horticultural oil', 'neem', 'extension']:
            if marker in text:
                score += 6
    if 'japanese beetle' in q:
        if 'japanese beetle' in title or 'japanese-beetle' in url:
            score += 30
        elif 'japanese beetle' not in text:
            score -= 45
        for marker in ['cdfa', 'uc ipm', 'ucanr', 'california', 'eradication', 'japanese beetle']:
            if marker in text:
                score += 7
    if 'last frost' in q:
        if not any(marker in text for marker in ['san ramon', '94582', 'zipcode', 'zip code', 'garden.org/apps/frost-dates']):
            score -= 35
        for marker in ['94582', 'san ramon', 'frost dates', 'planting calendar', 'almanac', 'garden.org']:
            if marker in text:
                score += 7
    if 'video' in q and ('pruning roses' in q or 'prune roses' in q):
        for marker in ['youtube.com', 'video', 'prune roses', 'pruning roses', 'extension']:
            if marker in text:
                score += 7
    if 'peat-free potting soil' in q:
        for marker in ['peat-free', 'potting soil', 'pittmoss', 'home depot', 'homedepot']:
            if marker in text:
                score += 7
    if 'succulent' in q:
        if 'succulent' not in text:
            score -= 25
        for marker in ['succulent', 'water', 'hot weather', 'morning', 'soil']:
            if marker in text:
                score += 5
    if 'video' not in q and 'youtube.com' in url:
        score -= 10

    return score


def _rank_results(results: List[Dict[str, str]], user_query: str) -> List[Dict[str, str]]:
    return sorted(
        results,
        key=lambda item: (_source_score(item, user_query), item.get('title', '')),
        reverse=True,
    )


def _build_summary(results: List[Dict[str, str]], max_items: int = 3, limit: int = 420) -> str:
    if not results:
        return 'Web search did not return usable results.'
    titles = [item.get('title', 'Source') for item in results[:max_items]]
    summary = f"Found {len(results)} web sources. Top sources: " + '; '.join(titles) + '.'
    return _clean_snippet(summary, limit=limit)


def search_web(user_query: str, max_results: int = 5) -> Dict[str, Any]:
    weather_result = _san_ramon_weather(user_query)
    if weather_result:
        return weather_result

    queries = _candidate_web_queries(user_query)
    start = time.perf_counter()

    all_results: List[Dict[str, str]] = []
    providers: List[str] = []
    for query in queries:
        results = _search_duckduckgo(query, max_results=max_results)
        provider = 'duckduckgo'
        if results is None:
            results = _search_duckduckgo_html(query, max_results=max_results)
            provider = 'duckduckgo-html' if results else provider
        if results:
            all_results.extend(results)
            providers.append(provider)
        if len(queries) == 1 and len(all_results) >= max_results * 2:
            break

    if not all_results:
        return {
            'ok': False,
            'provider': None,
            'query': queries[0],
            'queries': queries,
            'summary': 'Web search unavailable. DuckDuckGo package and HTML fallback both failed.',
            'results': [],
            'error': 'No web search provider available.',
            'latency_s': round(time.perf_counter() - start, 4),
        }

    cleaned_results = _rank_results(_clean_results(all_results), user_query)[:max_results]
    summary = _build_summary(cleaned_results)
    return {
        'ok': True,
        'provider': '+'.join(sorted(set(providers))) if providers else 'duckduckgo',
        'query': queries[0],
        'queries': queries,
        'summary': summary,
        'results': cleaned_results,
        'latency_s': round(time.perf_counter() - start, 4),
    }


def pretty_rows(rows: List[Dict[str, Any]], limit: int = 5) -> str:
    if not rows:
        return '[]'
    return json.dumps(rows[:limit], indent=2, default=str)


__all__.extend([
    'WRITEABLE_TABLES',
    'build_web_query',
    'execute_sql',
    'pretty_rows',
    'search_web',
])
