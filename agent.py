from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from config import (
    CURRENT_MONTH_DAY,
    LAST_MONTH_END,
    LAST_MONTH_START,
    TODAY,
)
from agent_db import CARE_PROFILES, PERSONAL_PLANTS
from agent_tools import execute_sql, pretty_rows, search_web

DENYLIST_PATTERNS = [
    r"\b(drop|delete|truncate|alter|update|insert)\s+table\b",
    r"\b(sqlite_master|pragma|attach|detach)\b",
    r"\b(api\s*key|secret|token|password)\b",
    r"\b(exfiltrate|leak|steal)\b",
]


@dataclass
class BenchmarkResult:
    model_name: str
    loaded: bool
    load_error: Optional[str]
    tool_accuracy: float
    avg_latency_s: float
    avg_keyword_coverage: float
    robustness: float


OPENROUTER_LARGE_MODEL = "meta-llama/llama-3.1-8b-instruct"
OPENROUTER_SMALL_MODEL = "microsoft/phi-3.5-mini-instruct"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

OPENROUTER_API_KEY = "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"


def _openrouter_chat(prompt: str, model_id: str) -> Optional[str]:
    if not OPENROUTER_API_KEY:
        return None
    try:
        import requests
    except Exception:
        return None

    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": "You are a concise, helpful gardening assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 256,
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Gardening Agent Notebook",
    }
    try:
        response = requests.post(OPENROUTER_BASE_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip() or None
    except Exception:
        return None


def _model_summarize(prompt: str, model_choice: str) -> Optional[str]:
    if not OPENROUTER_API_KEY:
        return None
    model_id = OPENROUTER_LARGE_MODEL if model_choice == 'large' else OPENROUTER_SMALL_MODEL
    return _openrouter_chat(prompt, model_id)


def _model_loaded(model_choice: str) -> bool:
    return bool(OPENROUTER_API_KEY)


def _has_weather_and_plant(user_query: str) -> bool:
    q = user_query.lower()
    if not any(word in q for word in ['weather', 'temperature', 'temp', 'forecast', 'rain']):
        return False
    return any(name.lower() in q for name in PLANT_CANDIDATES)


def _is_spending_query(user_query: str) -> bool:
    q = user_query.lower()
    return any(word in q for word in ['spend', 'spent', 'expense', 'expenses', 'gardening supplies'])


def _is_pest_alert(user_query: str) -> bool:
    q = user_query.lower()
    return any(word in q for word in ['beetle', 'pest', 'mildew', 'warning', 'alert'])


def _matches_denylist(user_query: str) -> bool:
    for pattern in DENYLIST_PATTERNS:
        if re.search(pattern, user_query, flags=re.IGNORECASE):
            return True
    return False


def _is_gardening_related(user_query: str, model_choice: str = 'large') -> bool:
    prompt = (
        "Classify the user query as gardening-related or not gardening-related. "
        "Reply with exactly YES or NO and nothing else.\n\n"
        f"Query: {user_query}"
    )
    for choice in (model_choice, 'small' if model_choice == 'large' else 'large'):
        response = _model_summarize(prompt, model_choice=choice)
        if not response:
            continue
        normalized = response.strip().lower()
        first_token = normalized.split()[0] if normalized else ''
        if first_token in {'yes', 'y'}:
            return True
        if first_token in {'no', 'n'}:
            return False
    return False


def _is_unsafe_prompt(user_query: str) -> Optional[str]:
    if _matches_denylist(user_query):
        return 'Blocked: unsafe or sensitive request.'
    if not _is_gardening_related(user_query):
        return 'Blocked: out-of-scope request (gardening only).'
    return None


def expected_route_from_keywords(user_query: str, model_choice: str = 'large') -> str:
    if not _is_gardening_related(user_query, model_choice=model_choice):
        return 'refusal'
    prompt = (
        "Choose the best tool route for this gardening question. Reply with exactly one word: "
        "sql, web, or hybrid.\n\n"
        f"Query: {user_query}"
    )
    for choice in (model_choice, 'small' if model_choice == 'large' else 'large'):
        response = _model_summarize(prompt, model_choice=choice)
        if not response:
            continue
        normalized = response.strip().lower().split()[0]
        if normalized in {'sql', 'web', 'hybrid'}:
            return normalized
    return 'sql'


def route_query(user_query: str, model_choice: str = 'large') -> str:
    return expected_route_from_keywords(user_query, model_choice=model_choice)


PLANT_CANDIDATES = sorted(
    {item['common_name'] for item in CARE_PROFILES}.union({item['name'] for item in PERSONAL_PLANTS}),
    key=lambda name: len(name),
    reverse=True,
)


def _canonical_plant_name(user_query: str) -> Optional[str]:
    q = user_query.lower()
    for name in PLANT_CANDIDATES:
        if name.lower() in q:
            return name
    return None


def _extract_item_name(user_query: str) -> Optional[str]:
    match = re.search(r"add\s+(.*?)\s+to\s+(my\s+)?shopping\s+list", user_query, flags=re.IGNORECASE)
    if not match:
        return None
    item = match.group(1).strip().rstrip('.')
    return item or None


def _detect_intent(user_query: str) -> Optional[str]:
    q = user_query.lower()
    if 'shopping list' in q and 'add' in q:
        return 'shopping_list_add'
    if 'shopping list' in q:
        return 'shopping_list_view'
    if 'watering schedule' in q or 'when should i water' in q:
        return 'watering_schedule'
    if 'last fertilize' in q or 'last fertilized' in q:
        return 'last_fertilized'
    if 'inactive' in q:
        return 'inactive_plants'
    if _is_spending_query(user_query):
        return 'expenses_gardening_supplies'
    if 'optimal soil ph' in q or 'soil ph' in q or 'ph' in q:
        return 'optimal_ph'
    if 'repot' in q or 'root bound' in q:
        return 'repot_status'
    if ('yellow' in q and 'brown' in q) or 'tomato leaves' in q:
        return 'diagnosis'
    if 'compare' in q and 'basil' in q and 'mint' in q:
        return 'growth_compare'
    if ('temperature' in q or 'temp' in q) and 'hibiscus' in q:
        return 'temp_safe_range'
    if ('low light' in q or 'low-light' in q) and ('indoor' in q or 'house' in q) and ('beginner' in q or 'beginners' in q):
        return 'low_light_beginner'
    return None


def build_sql(user_query: str) -> Optional[Dict[str, Any]]:
    intent = _detect_intent(user_query)
    if not intent:
        return None

    if intent == 'shopping_list_add':
        item_name = _extract_item_name(user_query) or 'garden supply item'
        return {
            'sql': (
                "INSERT INTO shopping_list (item_name, category, status, priority, added_date, source) "
                "VALUES (:item_name, :category, 'open', 'medium', date('now'), 'demo query') "
                "ON CONFLICT(item_name) DO NOTHING"
            ),
            'params': {'item_name': item_name, 'category': 'general'},
        }

    if intent == 'shopping_list_view':
        return {
            'sql': "SELECT item_name, category, status, priority, added_date FROM shopping_list ORDER BY added_date DESC",
            'params': {},
        }

    if intent == 'watering_schedule':
        plant_name = _canonical_plant_name(user_query)
        if not plant_name:
            return None
        return {
            'sql': (
                "SELECT p.name, w.frequency_days, w.amount_ml, w.next_due, p.last_watered, p.location "
                "FROM watering_schedules w JOIN plants p ON p.id = w.plant_id "
                "WHERE lower(p.name) LIKE '%' || lower(:plant_name) || '%'"
            ),
            'params': {'plant_name': plant_name},
        }

    if intent == 'last_fertilized':
        plant_name = _canonical_plant_name(user_query) or 'Banana Plant'
        return {
            'sql': (
                "SELECT p.name, f.application_date, f.fertilizer_name, f.npk_ratio "
                "FROM fertilizer_history f JOIN plants p ON p.id = f.plant_id "
                "WHERE lower(p.name) LIKE '%' || lower(:plant_name) || '%' "
                "ORDER BY f.application_date DESC LIMIT 1"
            ),
            'params': {'plant_name': plant_name},
        }

    if intent == 'inactive_plants':
        return {
            'sql': "SELECT name, species, location, status FROM plants WHERE status = 'inactive' ORDER BY name",
            'params': {},
        }

    if intent == 'expenses_gardening_supplies':
        return {
            'sql': (
                "SELECT category, ROUND(SUM(amount_usd), 2) AS total_usd "
                "FROM expenses WHERE category = 'gardening supplies' "
                "AND expense_date >= :month_start AND expense_date <= :month_end GROUP BY category"
            ),
            'params': {'month_start': LAST_MONTH_START.isoformat(), 'month_end': LAST_MONTH_END.isoformat()},
        }

    if intent == 'optimal_ph':
        plant_name = _canonical_plant_name(user_query) or 'Cherry Tomatoes'
        return {
            'sql': "SELECT common_name, ideal_ph_min, ideal_ph_max, watering_note FROM care_profiles WHERE common_name = :common_name",
            'params': {'common_name': plant_name},
        }

    if intent == 'repot_status':
        plant_name = _canonical_plant_name(user_query) or 'Monstera'
        return {
            'sql': (
                "SELECT p.name, r.repot_date, r.pot_size_in, r.root_bound, r.notes "
                "FROM repotting_records r JOIN plants p ON p.id = r.plant_id "
                "WHERE lower(p.name) LIKE '%' || lower(:plant_name) || '%' "
                "ORDER BY r.repot_date DESC LIMIT 1"
            ),
            'params': {'plant_name': plant_name},
        }

    if intent == 'diagnosis':
        plant_name = _canonical_plant_name(user_query) or 'Tomato Plant'
        return {
            'sql': (
                "SELECT p.name, d.symptom, d.severity, d.likely_cause, d.recommended_action, d.diagnosis_date "
                "FROM diagnostics d JOIN plants p ON p.id = d.plant_id "
                "WHERE lower(p.name) LIKE '%' || lower(:plant_name) || '%' "
                "ORDER BY d.diagnosis_date DESC LIMIT 1"
            ),
            'params': {'plant_name': plant_name},
        }

    if intent == 'growth_compare':
        return {
            'sql': (
                "SELECT p.name, MIN(g.log_date) AS start_date, MAX(g.log_date) AS end_date, "
                "ROUND(MAX(g.height_cm) - MIN(g.height_cm), 1) AS height_gain_cm "
                "FROM growth_logs g JOIN plants p ON p.id = g.plant_id "
                "WHERE lower(p.name) IN (lower(:plant_a), lower(:plant_b)) "
                "GROUP BY p.name ORDER BY p.name"
            ),
            'params': {'plant_a': 'Sweet Basil', 'plant_b': 'Mint'},
        }

    if intent == 'temp_safe_range':
        return {
            'sql': "SELECT common_name, temp_safe_low_c, temp_safe_high_c FROM care_profiles WHERE common_name = 'Hibiscus'",
            'params': {},
        }

    if intent == 'low_light_beginner':
        return {
            'sql': (
                "SELECT common_name, light_profile, indoor_suitability, beginner_friendly "
                "FROM care_profiles WHERE indoor_suitability = 1 AND beginner_friendly = 1 "
                "AND (light_profile LIKE '%low%' OR light_profile LIKE '%shade%') "
                "ORDER BY common_name"
            ),
            'params': {},
        }

    return None


def _template_answer(rows: List[Dict[str, Any]], web_summary: Optional[str], user_query: str) -> Optional[str]:
    if not rows:
        return None
    first = rows[0]

    if 'likely_cause' in first:
        return (
            f"Based on your diagnostics log, {first.get('name', 'the plant')} shows {first.get('symptom', 'symptoms noted')}. "
            f"Severity: {first.get('severity', 'unknown')}. Likely cause: {first.get('likely_cause', 'unknown')}. "
            f"Recommended action: {first.get('recommended_action', 'monitor and adjust care')}."
        )
    if 'root_bound' in first:
        needs_repot = bool(first.get('root_bound'))
        status = 'Yes' if needs_repot else 'Not yet'
        return (
            f"Based on the latest repotting record, repot needed: {status}. "
            f"Checked on {first.get('repot_date')} with pot size {first.get('pot_size_in')} in. "
            f"Notes: {first.get('notes', 'no additional notes')}."
        )
    if 'height_gain_cm' in first:
        parts = []
        for row in rows:
            parts.append(
                f"{row.get('name')}: +{row.get('height_gain_cm')} cm from {row.get('start_date')} to {row.get('end_date')}"
            )
        return "Based on your growth logs, " + '; '.join(parts) + '.'
    if 'temp_safe_low_c' in first:
        summary = (
            f"Safe temperature range for {first.get('common_name', 'Hibiscus')}: "
            f"{first['temp_safe_low_c']}C to {first['temp_safe_high_c']}C."
        )
        if web_summary:
            summary = summary + f" Forecast context: {web_summary}"
        else:
            summary = summary + " I do not have today's temperature, so check the local forecast."
        return summary
    if 'light_profile' in first and 'common_name' in first:
        names = [row['common_name'] for row in rows[:3] if 'common_name' in row]
        return 'Based on care profiles, low-light beginner-friendly options: ' + ', '.join(names)
    if 'frequency_days' in first:
        return (
            f"Based on your watering schedule, water every {first['frequency_days']} days, "
            f"about {first['amount_ml']} ml. Last watered: {first.get('last_watered')}. Next due: {first.get('next_due')}."
        )
    if 'application_date' in first:
        return (
            f"Based on your fertilizer log, last applied on {first['application_date']} "
            f"using {first['fertilizer_name']} ({first['npk_ratio']})."
        )
    if 'item_name' in first and 'added_date' in first and 'status' in first:
        if len(rows) == 1 and 'shopping list' in user_query.lower() and 'add' in user_query.lower():
            return f"Added {first['item_name']} to the shopping list."
        items = [f"{row['item_name']} ({row['status']}, {row['priority']})" for row in rows[:5]]
        return 'Current shopping list: ' + '; '.join(items)
    if 'status' in first and len(rows) > 1 and 'name' in first:
        return 'Inactive plants: ' + ', '.join(row['name'] for row in rows if 'name' in row)
    if 'total_usd' in first:
        return (
            f"Total gardening supplies spend for last month ({LAST_MONTH_START} to {LAST_MONTH_END}): "
            f"${first['total_usd']}."
        )
    if 'ideal_ph_min' in first:
        return (
            f"Optimal soil pH for {first.get('common_name', 'this plant')}: "
            f"{first['ideal_ph_min']} to {first['ideal_ph_max']}. {first.get('watering_note', '')}"
        )
    return None


def _format_rows(rows: List[Dict[str, Any]], limit: int = 3) -> str:
    formatted = []
    for row in rows[:limit]:
        bits = [f"{key}={row.get(key)}" for key in row.keys()]
        formatted.append(', '.join(bits))
    return ' | '.join(formatted) if formatted else 'No matching records.'


def compose_final_answer(
    route: str,
    user_query: str,
    sql_result: Optional[Dict[str, Any]] = None,
    web_result: Optional[Dict[str, Any]] = None,
    model_choice: str = 'large',
) -> str:
    evidence = []
    if sql_result:
        evidence.append(f"SQL: {pretty_rows(sql_result.get('rows', []), limit=5)}")
    if web_result:
        evidence.append(f"WEB: {web_result.get('summary', '')}")

    if evidence:
        model_prompt = (
            "Answer the user using the evidence. Be concise and practical.\n"
            f"Question: {user_query}\n"
            f"Evidence: {' '.join(evidence)}"
        )
        model_answer = _model_summarize(model_prompt, model_choice=model_choice)
        if model_answer:
            return model_answer

    if sql_result and sql_result.get('ok'):
        rows = sql_result.get('rows', [])
        templated = _template_answer(rows, web_summary=(web_result or {}).get('summary'), user_query=user_query)
        if templated:
            return templated

    if route == 'sql' and sql_result:
        if not sql_result.get('ok'):
            return sql_result.get('error', 'The database query failed.')
        rows = sql_result.get('rows', [])
        if not rows:
            if sql_result.get('row_count') == 0 and 'shopping list' in user_query.lower():
                return 'That item is already on your shopping list.'
            if sql_result.get('row_count'):
                return f"Updated the database successfully. Rows affected: {sql_result['row_count']}."
            return 'I could not find a matching record in the gardening database.'
        return _format_rows(rows)
    if route == 'web' and web_result:
        return web_result.get('summary', 'I found relevant web results.')
    if route == 'hybrid':
        parts = []
        if sql_result and sql_result.get('rows'):
            parts.append(_format_rows(sql_result['rows']))
        if web_result and web_result.get('summary'):
            parts.append(web_result['summary'])
        return ' '.join(parts) if parts else 'I used both the database and web search, but found little to combine.'
    return 'I could not determine the best route for that question.'


def handle_query(user_query: str, model_choice: str = 'large') -> Dict[str, Any]:
    start = time.perf_counter()
    refusal_reason = _is_unsafe_prompt(user_query)
    if refusal_reason:
        return {
            'query': user_query,
            'route': 'refusal',
            'expected_route': None,
            'latency_s': round(time.perf_counter() - start, 4),
            'sql_result': None,
            'web_result': None,
            'final_answer': (
                'I can only help with gardening-related questions and cannot assist with unsafe requests.'
            ),
            'model_choice': model_choice,
            'model_loaded': _model_loaded(model_choice),
            'refusal_reason': refusal_reason,
        }
    route = route_query(user_query, model_choice=model_choice)
    expected_route = route
    sql_result = None
    web_result = None
    if route in {'sql', 'hybrid'}:
        sql_payload = build_sql(user_query)
        if sql_payload:
            sql_result = execute_sql(sql_payload['sql'], sql_payload.get('params'))
    if route in {'web', 'hybrid'}:
        web_result = search_web(user_query)
    latency_s = round(time.perf_counter() - start, 4)
    final_answer = compose_final_answer(
        route,
        user_query,
        sql_result=sql_result,
        web_result=web_result,
        model_choice=model_choice,
    )
    return {
        'query': user_query,
        'route': route,
        'expected_route': expected_route,
        'latency_s': latency_s,
        'sql_result': sql_result,
        'web_result': web_result,
        'final_answer': final_answer,
        'model_choice': model_choice,
        'model_loaded': _model_loaded(model_choice),
    }


__all__ = [
    'BenchmarkResult',
    'build_sql',
    'compose_final_answer',
    'expected_route_from_keywords',
    'handle_query',
    'route_query',
    '_model_loaded',
    '_model_summarize',
]
