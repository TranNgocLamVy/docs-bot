from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(dotenv_path=ENV_PATH, override=False)


def get_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)

    if raw_value is None or raw_value.strip() == "":
        return default

    try:
        value = int(raw_value)
    except ValueError as exc:
        return default

    if value <= 0:
        return default

    return value


BASE_URL = os.getenv("BASE_URL", "localhost:3000").rstrip("/")
ARTICLE_FETCH_SIZE = get_int_env("ARTICLE_FETCH_SIZE", 50)