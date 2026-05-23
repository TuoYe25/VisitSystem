"""应用配置"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR / 'data' / 'visitsystem.db'}",
)

# 访视窗口容差（天），超出窗口的随访标记为"超窗"
WINDOW_TOLERANCE_DAYS = int(os.getenv("WINDOW_TOLERANCE_DAYS", "3"))
