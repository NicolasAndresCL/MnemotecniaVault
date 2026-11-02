from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", os.environ.get("TEST_DATABASE_URL", "sqlite://"))
os.environ.setdefault("TIMEZONE", "America/Santiago")

import pytest  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db import Base, get_engine, init_db, reset_caches, session_scope  # noqa: E402


@pytest.fixture
def db():
    """BD limpia por test (SQLite en memoria, o el Postgres de TEST_DATABASE_URL en CI)."""
    get_settings.cache_clear()
    reset_caches()
    init_db()
    with session_scope() as s:
        yield s
    Base.metadata.drop_all(get_engine())
