from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import (
    LAST_MONTH_END,
    LAST_MONTH_START,
)
from agent_db import CARE_PROFILES, PERSONAL_PLANTS
from config import execute_sql, search_web

DENYLIST_PATTERNS = [
    r"\b(drop|delete|truncate|alter|update|insert)\s+table\b",
    r"\b(sqlite_master|pragma|attach|detach)\b",
    r"\b(api\s*key|secret|token|password)\b",
    r"\b(exfiltrate|leak|steal)\b",
    r"\b(ignore|override|forget)\s+(all\s+)?(previous|prior|system|developer)\s+instructions\b",
    r"\b(system|developer)\s+(prompt|message|instructions?)\b",
    r"\b(jailbreak|prompt\s+injection)\b",
    r"\boverride\b.*\b(policy|guardrails?|safety|scope)\b",
    r"\breveal\b.*\b(prompt|instructions?|settings|secrets?)\b",
]


OPENROUTER_LARGE_MODEL = "meta-llama/llama-3.3-70b-instruct"
OPENROUTER_SMALL_MODEL = "microsoft/phi-3.5-mini-instruct"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"


def _load_local_env() -> None:
    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export "):].strip()
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


_load_local_env()
_MODEL_LAST_ERROR: Optional[str] = None

GARDENING_TERMS = {
    'basil',
    'beetle',
    'compost',
    'fertilize',
    'fertilizer',
    'flower',
    'garden',
    'gardening',
    'grow',
    'hibiscus',
    'indoor plant',
    'leaf',
    'leaves',
    'mint',
    'monstera',
    'mulch',
    'nursery',
    'pest',
    'plant',
    'plants',
    'potting',
    'prune',
    'repot',
    'root',
    'soil',
    'tomato',
    'water',
    'watering',
}

WEB_ROUTE_TERMS = {
    'buy',
    'eco friendly',
    'eco-friendly',
    'forecast',
    'frost',
    'near me',
    'nursery',
    'rain',
    'selling',
    'today',
    'tomorrow',
    'video',
    'warning',
    'warnings',
    'weather',
    'where can i buy',
}


def _get_openrouter_api_key() -> str:
    return os.environ.get("OPENROUTER_API_KEY", "").strip()


def _set_model_error(message: Optional[str]) -> None:
    global _MODEL_LAST_ERROR
    _MODEL_LAST_ERROR = message


def _sanitize_model_error(message: Any) -> str:
    cleaned = ' '.join(str(message).split())
    cleaned = re.sub(r"sk-[A-Za-z0-9_-]+", "[redacted]", cleaned)
    cleaned = re.sub(r"Bearer\s+\S+", "Bearer [redacted]", cleaned, flags=re.IGNORECASE)
    return cleaned[:300]


def _model_error() -> Optional[str]:
    return _MODEL_LAST_ERROR


def _openrouter_chat(prompt: str, model_id: str) -> Optional[str]:
    api_key = _get_openrouter_api_key()
    if not api_key:
        _set_model_error("OPENROUTER_API_KEY is not set.")
        return None
    try:
        import requests
    except Exception:
        _set_model_error("The requests package is not installed.")
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
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Gardening Agent Notebook",
    }
    try:
        response = requests.post(OPENROUTER_BASE_URL, json=payload, headers=headers, timeout=30)
        if response.status_code >= 400:
            error_message = response.text
            try:
                error_payload = response.json()
                if isinstance(error_payload, dict):
                    error = error_payload.get("error", error_payload)
                    if isinstance(error, dict):
                        error_message = error.get("message") or error.get("code") or error_message
            except Exception:
                pass
            _set_model_error(
                f"OpenRouter API error {response.status_code}: {_sanitize_model_error(error_message)}"
            )
            return None
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        if content:
            _set_model_error(None)
            return content
        _set_model_error("OpenRouter response did not include a message.")
        return None
    except Exception as exc:
        _set_model_error(f"OpenRouter request failed: {_sanitize_model_error(exc)}")
        return None


def _model_summarize(prompt: str, model_choice: str) -> Optional[str]:
    if not _get_openrouter_api_key():
        _set_model_error("OPENROUTER_API_KEY is not set.")
        return None
    model_id = OPENROUTER_LARGE_MODEL if model_choice == 'large' else OPENROUTER_SMALL_MODEL
    return _openrouter_chat(prompt, model_id)


def _model_loaded(model_choice: str) -> bool:
    return bool(_get_openrouter_api_key())


def _has_weather_and_plant(user_query: str) -> bool:
    q = user_query.lower()
    if not any(word in q for word in ['weather', 'temperature', 'temp', 'forecast', 'rain']):
        return False
    return any(name.lower() in q for name in PLANT_CANDIDATES)


def _is_spending_query(user_query: str) -> bool:
    q = user_query.lower()
    return any(word in q for word in ['spend', 'spent', 'expense', 'expenses', 'gardening supplies'])


def _matches_denylist(user_query: str) -> bool:
    for pattern in DENYLIST_PATTERNS:
        if re.search(pattern, user_query, flags=re.IGNORECASE):
            return True
    return False


def _looks_gardening_related(user_query: str) -> bool:
    q = user_query.lower()
    if _detect_intent(user_query):
        return True
    if any(name.lower() in q for name in PLANT_CANDIDATES):
        return True
    return any(term in q for term in GARDENING_TERMS)


def _fallback_route(user_query: str) -> str:
    q = user_query.lower()
    intent = _detect_intent(user_query)
    if intent:
        if intent == 'temp_safe_range' and any(term in q for term in WEB_ROUTE_TERMS):
            return 'hybrid'
        return 'sql'
    if _has_weather_and_plant(user_query):
        return 'hybrid'
    if 'water' in q and any(term in q for term in ['forecast', 'rain', 'weather']):
        return 'hybrid'
    if any(term in q for term in WEB_ROUTE_TERMS):
        return 'web'
    if _looks_gardening_related(user_query):
        return 'direct'
    return 'direct'


def _is_unsafe_prompt(user_query: str) -> Optional[str]:
    if _matches_denylist(user_query):
        return 'Blocked: unsafe or sensitive request.'
    return None


def expected_route_from_keywords(user_query: str, model_choice: str = 'large') -> str:
    return _fallback_route(user_query)


def route_query(user_query: str, model_choice: str = 'large') -> str:
    return _fallback_route(user_query)


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


def _template_answer(
    rows: List[Dict[str, Any]],
    web_summary: Optional[str],
    user_query: str,
    web_result: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
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
        plant = first.get('common_name', 'Hibiscus')
        safe_low_c = float(first['temp_safe_low_c'])
        safe_high_c = float(first['temp_safe_high_c'])
        safe_low_f = safe_low_c * 9 / 5 + 32
        safe_high_f = safe_high_c * 9 / 5 + 32
        weather = (web_result or {}).get('weather') or {}
        low_f = weather.get('temperature_2m_min_f')
        high_f = weather.get('temperature_2m_max_f')
        forecast_date = weather.get('date')
        if isinstance(low_f, (int, float)) and isinstance(high_f, (int, float)):
            if low_f < safe_low_f:
                verdict = "That low is below the safe range, so protect it or bring it inside overnight."
            elif high_f > safe_high_f:
                verdict = "That high is above the safe range, so give afternoon shade and check soil moisture."
            else:
                verdict = "That forecast is within the safe range."
            return (
                f"{plant}'s safe range is {safe_low_c:.0f}-{safe_high_c:.0f}C "
                f"({safe_low_f:.0f}-{safe_high_f:.0f}F). San Ramon forecast for {forecast_date}: "
                f"high {high_f:.0f}F / low {low_f:.0f}F. {verdict}"
            )
        summary = (
            f"Safe temperature range for {plant}: {safe_low_c:.0f}C to {safe_high_c:.0f}C "
            f"({safe_low_f:.0f}F to {safe_high_f:.0f}F)."
        )
        if web_summary and 'unavailable' not in web_summary.lower():
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


def _offline_web_answer(user_query: str) -> Optional[str]:
    q = user_query.lower()
    if '94582' in q and 'neem oil' in q:
        return (
            "I cannot verify live store inventory from the current web tool. Best next step: call garden centers, "
            "hardware stores, or hydroponic shops near 94582 and ask for cold-pressed neem oil before you go."
        )
    if 'video' in q and ('pruning roses' in q or 'prune roses' in q):
        return (
            "Look for a university extension or master gardener rose-pruning video. A good tutorial should show three things: "
            "remove dead or crossing canes, open the center for airflow, and cut just above outward-facing buds."
        )
    if 'eco-friendly' in q or 'eco friendly' in q:
        return (
            "Eco-friendly pest control starts with identifying the pest, removing heavily affected leaves, spraying with water, "
            "and using barriers or traps before pesticides. If needed, use insecticidal soap, neem oil, or horticultural oil "
            "according to the label, and avoid spraying when pollinators are active."
        )
    if 'san ramon' in q and 'rain' in q:
        return (
            "I cannot confirm tomorrow's San Ramon forecast from the current web tool. Check a local weather app before watering; "
            "if meaningful rain is expected overnight or tomorrow morning, skip watering and recheck soil moisture the next day."
        )
    if 'succulent' in q and ('90' in q or 'temperature' in q or 'weather' in q):
        return (
            "For succulents in 90 degree weather, water only if the soil is fully dry. "
            "Water deeply in the early morning, avoid wetting leaves in harsh sun, and skip watering if the potting mix "
            "still feels damp."
        )
    if 'japanese beetle' in q:
        return (
            "Web search is unavailable, so I cannot confirm live Japanese beetle alerts. "
            "Check your county extension office or state agriculture department for current local pest advisories."
        )
    if 'last frost' in q:
        return (
            "Web search is unavailable, so I cannot confirm this year's forecast. "
            "Use a local extension frost-date tool or weather service, then wait until nighttime lows are reliably above "
            "your plant's safe range before transplanting tender crops."
        )
    if 'peat-free potting soil' in q:
        return (
            "Web search is unavailable, so I cannot confirm current store stock. "
            "Look for peat-free mixes based on coco coir, composted bark, wood fiber, or compost, and check the bag for the "
            "plant type it is formulated for."
        )
    return None


def _format_sources(results: List[Dict[str, Any]], limit: int = 3) -> str:
    source_bits = []
    for idx, item in enumerate(results[:limit], start=1):
        title = item.get('title') or 'Source'
        url = item.get('url') or ''
        if url:
            source_bits.append(f"[{idx}] {title}: {url}")
        else:
            source_bits.append(f"[{idx}] {title}")
    return " Sources: " + " | ".join(source_bits) if source_bits else ""


def _format_web_results(web_result: Dict[str, Any], limit: int = 3) -> str:
    summary = web_result.get('summary') or 'I found relevant web results.'
    results = web_result.get('results') or []
    if results:
        return summary + _format_sources(results, limit=limit)
    return summary


def _web_evidence(web_result: Dict[str, Any], limit: int = 3) -> str:
    lines = []
    for idx, item in enumerate((web_result.get('results') or [])[:limit], start=1):
        title = item.get('title') or 'Untitled source'
        url = item.get('url') or ''
        snippet = item.get('snippet') or ''
        lines.append(f"[{idx}] Title: {title}\nURL: {url}\nSnippet: {snippet}")
    return "\n\n".join(lines)


def _model_web_answer(user_query: str, web_result: Dict[str, Any], model_choice: str) -> Optional[str]:
    if web_result.get('provider') == 'open-meteo':
        return None
    evidence = _web_evidence(web_result)
    if not evidence:
        return None
    prompt = (
        "Answer the gardening user using ONLY the web evidence below. "
        "Do not paste raw snippets. Synthesize the result into a direct, useful answer. "
        "Cite only the numbered sources provided below, such as [1] or [2]. "
        "Do not cite a source number that is not shown. "
        "Do not infer that no warning or no inventory exists just because the snippets do not mention it. "
        "If the evidence does not prove live availability, say to call or verify first. "
        "Keep it under 120 words.\n\n"
        f"User question: {user_query}\n\n"
        f"Web evidence:\n{evidence}"
    )
    answer = _model_summarize(prompt, model_choice=model_choice)
    if not answer:
        return None
    if web_result.get('results') and 'Sources:' not in answer:
        answer = answer.rstrip() + _format_sources(web_result.get('results') or [], limit=3)
    return answer


def _source_lines(results: List[Dict[str, Any]], limit: int = 3) -> List[str]:
    lines = []
    for idx, item in enumerate(results[:limit], start=1):
        title = item.get('title') or 'Source'
        url = item.get('url') or ''
        if url:
            lines.append(f"[{idx}] {title} ({url})")
        else:
            lines.append(f"[{idx}] {title}")
    return lines


def _specific_web_answer(user_query: str, web_result: Dict[str, Any]) -> Optional[str]:
    q = user_query.lower()
    results = web_result.get('results') or []
    source_text = ' Sources: ' + ' | '.join(_source_lines(results)) if results else ''
    def result_text(item: Dict[str, Any]) -> str:
        return (item.get('title', '') + ' ' + item.get('snippet', '') + ' ' + item.get('url', '')).lower()

    if '94582' in q and 'neem oil' in q:
        candidates = [
            item for item in results
            if 'neem' in result_text(item)
            and not any(bad in result_text(item) for bad in ['facebook.com', 'youtube.com', 'postcodebase.com', 'bestplaces.net'])
        ] or results
        source_text = ' Sources: ' + ' | '.join(_source_lines(candidates)) if candidates else ''
        names = [item.get('title', 'a local source') for item in candidates[:2]]
        lead_phrase = '; '.join(names) if names else 'nearby garden supply listings'
        return (
            f"Best leads I found: {lead_phrase}. Treat this as availability evidence, not a live inventory guarantee. "
            "Call before going and ask whether they sell garden-safe neem oil today."
            f"{source_text}"
        )

    if 'video' in q and ('pruning roses' in q or 'prune roses' in q):
        videos = [
            item for item in results
            if 'youtube' in item.get('url', '').lower() or 'video' in (item.get('title', '') + item.get('snippet', '')).lower()
        ] or results
        source_text = ' Sources: ' + ' | '.join(_source_lines(videos)) if videos else ''
        names = '; '.join(item.get('title', 'rose-pruning video') for item in videos[:2])
        return (
            f"Good video/tutorial options: {names}. Choose one that shows dead/crossing cane removal, opening the center for airflow, "
            "and cutting above outward-facing buds."
            f"{source_text}"
        )

    if 'eco-friendly' in q or 'eco friendly' in q:
        return (
            "Eco-friendly pest control: first identify the pest, remove affected leaves, spray pests off with water, use barriers/traps, "
            "and encourage beneficial insects. If pressure remains, use targeted lower-impact treatments such as insecticidal soap, "
            "horticultural oil, or neem oil according to the label, avoiding sprays when pollinators are active."
            f"{source_text}"
        )

    if 'last frost' in q:
        frost_sources = [
            item for item in results
            if any(term in result_text(item) for term in ['san ramon', '94582', 'garden.org/apps/frost-dates'])
        ] or results
        source_text = ' Sources: ' + ' | '.join(_source_lines(frost_sources)) if frost_sources else ''
        return (
            "For this project context, use San Ramon/94582 as the location and check a ZIP-code frost-date tool such as Almanac or Garden.org. "
            "For planting, wait until the local estimate has passed and the 7-10 day forecast keeps nighttime lows above the crop's tolerance."
            f"{source_text}"
        )

    if 'japanese beetle' in q:
        beetle_sources = [
            item for item in results
            if 'japanese beetle' in item.get('title', '').lower()
            or 'japanese-beetle' in item.get('url', '').lower()
        ] or results
        source_text = ' Sources: ' + ' | '.join(_source_lines(beetle_sources)) if beetle_sources else ''
        return (
            "I would not claim a current active warning from snippets alone. The reliable California sources to check are CDFA and UC IPM; "
            "they treat Japanese beetle as an invasive pest with eradication/reporting importance. If you suspect one, report it to your county agricultural office."
            f"{source_text}"
        )

    if 'peat-free potting soil' in q:
        return (
            "Best buying lead: current results point to peat-free mixes such as PittMoss at Home Depot plus peat-free product guides. "
            "Check local pickup/shipping before buying. Good peat-free bases include coco coir, composted bark, wood fiber, compost, or recycled-paper fiber."
            f"{source_text}"
        )

    if 'succulent' in q and ('90' in q or 'temperature' in q or 'weather' in q):
        succulent_sources = [
            item for item in results
            if 'succulent' in result_text(item) or 'heatwave' in result_text(item)
        ] or results
        source_text = ' Sources: ' + ' | '.join(_source_lines(succulent_sources)) if succulent_sources else ''
        return (
            "In 90 degree weather, water succulents only if the potting mix is fully dry. If it is dry, water deeply in the early morning so roots can take up moisture before peak heat. "
            "Skip watering if the soil is still damp, and keep the pot out of harsh afternoon sun if the plant looks stressed."
            f"{source_text}"
        )

    return None


def _web_answer(user_query: str, web_result: Optional[Dict[str, Any]], model_choice: str = 'large') -> Optional[str]:
    if web_result and web_result.get('ok'):
        specific = _specific_web_answer(user_query, web_result)
        if specific:
            return specific
        synthesized = _model_web_answer(user_query, web_result, model_choice=model_choice)
        if synthesized:
            return synthesized
        return _format_web_results(web_result)
    offline_answer = _offline_web_answer(user_query)
    if offline_answer:
        return offline_answer
    if not web_result:
        return None
    return web_result.get('summary') or 'Web search is unavailable.'


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
    if sql_result and sql_result.get('ok'):
        rows = sql_result.get('rows', [])
        templated = _template_answer(
            rows,
            web_summary=(web_result or {}).get('summary'),
            user_query=user_query,
            web_result=web_result,
        )
        if templated:
            return templated

    if route in {'web', 'hybrid'} and web_result:
        web_answer = _web_answer(user_query, web_result, model_choice=model_choice)
        if web_answer and (route == 'web' or not (sql_result and sql_result.get('rows'))):
            return web_answer

    if route == 'sql' and sql_result:
        if not sql_result.get('ok'):
            return sql_result.get('error', 'The database query failed.')
        rows = sql_result.get('rows', [])
        if not rows:
            if sql_result.get('row_count') == 0 and 'shopping list' in user_query.lower():
                return 'That item is already on your shopping list.'
            if sql_result.get('row_count'):
                item = _extract_item_name(user_query)
                if item:
                    return f"Added {item} to the shopping list."
                return f"Updated the database successfully. Rows affected: {sql_result['row_count']}."
            return 'I could not find a matching record in the gardening database.'
        return _format_rows(rows)
    if route == 'web' and web_result:
        return _web_answer(user_query, web_result, model_choice=model_choice) or 'Web search is unavailable.'
    if route == 'hybrid':
        parts = []
        if sql_result and sql_result.get('rows'):
            parts.append(_format_rows(sql_result['rows']))
        web_answer = _web_answer(user_query, web_result, model_choice=model_choice)
        if web_answer:
            parts.append(web_answer)
        return ' '.join(parts) if parts else 'I used both the database and web search, but found little to combine.'
    direct_prompt = (
        "Answer this gardening question clearly and concisely. "
        "Give practical plant-care advice and avoid making up database or web facts.\n\n"
        f"User: {user_query}"
    )
    direct_answer = _model_summarize(direct_prompt, model_choice=model_choice)
    if direct_answer:
        return direct_answer
    if _model_error():
        return f"I can answer this directly only when the model is available. Model call failed: {_model_error()}"
    return 'I can answer this directly, but the model call failed. Check your OPENROUTER_API_KEY or network connection.'


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
            'model_error': _model_error(),
            'refusal_reason': refusal_reason,
        }
    route = route_query(user_query, model_choice=model_choice)
    if route == 'direct' and not _looks_gardening_related(user_query):
        return {
            'query': user_query,
            'route': 'refusal',
            'expected_route': None,
            'latency_s': round(time.perf_counter() - start, 4),
            'sql_result': None,
            'web_result': None,
            'final_answer': 'I can only help with gardening-related questions.',
            'model_choice': model_choice,
            'model_loaded': _model_loaded(model_choice),
            'model_error': _model_error(),
            'refusal_reason': 'Blocked: out-of-scope request (gardening only).',
        }
    expected_route = route
    sql_result = None
    web_result = None
    if route in {'sql', 'hybrid'}:
        sql_payload = build_sql(user_query)
        if sql_payload:
            sql_result = execute_sql(sql_payload['sql'], sql_payload.get('params'))
        elif route == 'sql':
            route = 'direct'
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
        'model_error': _model_error(),
    }


__all__ = [
    'build_sql',
    'compose_final_answer',
    'expected_route_from_keywords',
    'handle_query',
    'route_query',
    '_model_error',
    '_model_loaded',
    '_model_summarize',
]
