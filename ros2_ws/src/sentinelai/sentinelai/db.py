"""Module de gestion de base de données SQLite pour SentinelAI."""

import sqlite3
from datetime import datetime
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "sentinel.db"

def get_connection(db_path: Path | str = DEFAULT_DB_PATH):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn

def get_user_by_code(code_id: str, db_path: Path | str = DEFAULT_DB_PATH) -> dict | None:
    """Récupère un utilisateur actif par son code identifiant."""
    with get_connection(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT id, code_id, name, grp, level, zone, active FROM users WHERE code_id = ?", (code_id,))
        row = cur.fetchone()
        if row:
            return dict(row)
        return None

def log_event(kind: str, code_id: str | None, status: str, persons: int = 0, snapshot: str | None = None, db_path: Path | str = DEFAULT_DB_PATH) -> int:
    """Enregistre un événement dans la table events."""
    ts = datetime.now().isoformat(timespec="seconds")
    with get_connection(db_path) as con:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO events (ts, kind, code_id, status, persons, snapshot) VALUES (?, ?, ?, ?, ?, ?)",
            (ts, kind, code_id, status, persons, snapshot)
        )
        return cur.lastrowid

def get_recent_events(limit: int = 50, db_path: Path | str = DEFAULT_DB_PATH) -> list[dict]:
    """Récupère les derniers événements enregistrés."""
    with get_connection(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT id, ts, kind, code_id, status, persons, snapshot FROM events ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cur.fetchall()]

def get_all_users(db_path: Path | str = DEFAULT_DB_PATH) -> list[dict]:
    """Récupère tous les utilisateurs."""
    with get_connection(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT id, code_id, name, grp, level, zone, active FROM users ORDER BY name ASC")
        return [dict(row) for row in cur.fetchall()]
