#!/usr/bin/env python3
"""Nettoyage des événements et des snapshots de plus de 30 jours (SentinelAI)."""

import os
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "sentinel.db"
SNAPSHOT_DIR = BASE_DIR / "data" / "snapshots"
RETENTION_DAYS = 30

def cleanup():
    cutoff = (datetime.now() - timedelta(days=RETENTION_DAYS)).isoformat(timespec="seconds")
    cutoff_time = time.time() - (RETENTION_DAYS * 86400)
    
    # 1. Nettoyage de la base de données
    if DB_PATH.exists():
        with sqlite3.connect(DB_PATH) as con:
            cur = con.cursor()
            cur.execute("DELETE FROM events WHERE ts < ?", (cutoff,))
            deleted = cur.rowcount
            print(f"[Nettoyage DB] {deleted} événement(s) purgé(s) antérieur(s) à {cutoff}.")

    # 2. Nettoyage des snapshots
    if SNAPSHOT_DIR.exists():
        purged_files = 0
        for f in SNAPSHOT_DIR.glob("*.jpg"):
            if f.stat().st_mtime < cutoff_time:
                try:
                    f.unlink()
                    purged_files += 1
                except Exception as e:
                    print(f"Erreur suppression {f}: {e}")
        print(f"[Nettoyage Snapshots] {purged_files} capture(s) supprimée(s).")

if __name__ == "__main__":
    cleanup()
