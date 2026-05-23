"""应用配置管理"""

import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据目录
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# 数据库配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DATA_DIR / 'visitsystem.db'}"
)

# 应用配置
APP_NAME = "受试者随访提醒与访视窗口计算系统"
APP_VERSION = "0.1.0"
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# 访视窗口配置（天数）
DEFAULT_WINDOW_DAYS = 3  # 默认访视窗口为计划日期前后 ±3 天

# 提醒配置
DEFAULT_REMIND_DAYS_BEFORE = 1  # 默认提前 1 天提醒
