#!/usr/bin/env python3
"""Initialisation de la base de données SQLite pour SentinelAI."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "sentinel.db"

USERS = [
    ("user_demo", "Alice Martin", "Technique", 1, "zone_libre", 1),
    ("user_admin", "Bob Dupont", "Direction", 3, "zone_interdite", 1),
    ("user_guest", "Charlie Durand", "Visiteur", 1, "zone_libre", 1),
]

def init_db(db_path: Path = DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            grp TEXT NOT NULL,
            level INTEGER NOT NULL,
            zone TEXT NOT NULL,
            active INTEGER DEFAULT 1
        );
        """)
        con.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            kind TEXT NOT NULL,
            code_id TEXT,
            status TEXT NOT NULL,
            persons INTEGER DEFAULT 0,
            snapshot TEXT
        );
        """)

        # Insertion des utilisateurs d'exemple s'ils n'existent pas
        for code_id, name, grp, level, zone, active in USERS:
            con.execute("""
            INSERT OR IGNORE INTO users (code_id, name, grp, level, zone, active)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (code_id, name, grp, level, zone, active))

    print(f"Base de donnees initialisee : {db_path}")

if __name__ == "__main__":
    init_db()
