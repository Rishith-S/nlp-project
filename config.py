from __future__ import annotations

import json
import os
import re
import sqlite3
import statistics
import textwrap
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import pandas as pd
except ImportError:
    pd = None

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
