"""Unit tests for SentinelAI SQLite database."""

import tempfile
from pathlib import Path
import pytest
from sentinelai.db import get_user_by_code, log_event, get_recent_events, get_all_users
from scripts.seed_db import init_db

@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        db_path = Path(f.name)
        init_db(db_path)
        yield db_path

def test_user_retrieval(temp_db):
    user = get_user_by_code("user_demo", temp_db)
    assert user is not None
    assert user["name"] == "Alice Martin"
    assert user["grp"] == "Technique"
    assert user["level"] == 1

def test_unknown_user_retrieval(temp_db):
    user = get_user_by_code("non_existent", temp_db)
    assert user is None

def test_event_logging(temp_db):
    event_id = log_event("scan", "user_demo", "ok", persons=1, snapshot=None, db_path=temp_db)
    assert event_id > 0
    events = get_recent_events(limit=10, db_path=temp_db)
    assert len(events) == 1
    assert events[0]["code_id"] == "user_demo"
    assert events[0]["status"] == "ok"

def test_get_all_users(temp_db):
    users = get_all_users(temp_db)
    assert len(users) >= 3
