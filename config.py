import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / ".env")

PAYI_BASE_URL = os.environ.get("PAYI_BASE_URL", "").rstrip("/")
PAYI_API_KEY = os.environ.get("PAYI_API_KEY", "")
DEFAULT_TIME_RANGE_DAYS = 7

REPORT_IDS: dict[int, str] = {}
for i in range(1, 9):
    val = os.environ.get(f"REPORT_ID_{i}", "")
    if val:
        REPORT_IDS[i] = val
