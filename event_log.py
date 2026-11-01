"""Journal des événements SentinelAI (SQLite). Aucune vidéo ni image n'est stockée."""
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from access_rules import AUTHORIZED, FORBIDDEN, UNCONFIRMED, DEGRADED

DB_PATH = Path(__file__).with_name("sentinel_events.db")
RETENTION_DAYS = 30  # les événements plus anciens sont supprimés au démarrage

REASONS = {
    AUTHORIZED: "présence conforme aux droits",
    FORBIDDEN: "badge sans droit sur cette zone",
    UNCONFIRMED: "zone restreinte sans badge valide",
    DEGRADED: "luminosité insuffisante, détection peu fiable",
}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def init_db():
    """Crée la table si besoin et purge les événements trop anciens."""
    cutoff = (datetime.now() - timedelta(days=RETENTION_DAYS)).isoformat(timespec="seconds")
    with closing(sqlite3.connect(DB_PATH)) as con, con:
        con.execute("""CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            track_id INTEGER,
            zone TEXT,
            badge TEXT,
            state TEXT NOT NULL,
            reason TEXT NOT NULL)""")
        con.execute("DELETE FROM events WHERE ts < ?", (cutoff,))


def _insert(track_id, zone, badge, state, reason):
    with closing(sqlite3.connect(DB_PATH)) as con, con:
        con.execute("INSERT INTO events (ts, track_id, zone, badge, state, reason) VALUES (?, ?, ?, ?, ?, ?)",
                    (_now(), track_id, zone, badge, state, reason))


def record_person(track_id, zone, badge, state):
    """Enregistre le changement d'état confirmé d'une personne suivie."""
    _insert(track_id, zone, badge, state, REASONS[state])
    print(f"[EVENT] ID {track_id} | zone={zone} | badge={badge or 'aucun'} | etat={state}")


def record_vision(vision_state, brightness):
    """Enregistre un changement de qualité de vision (ok / degraded)."""
    if vision_state == "ok":
        state, reason = "vision normale", f"luminosité {brightness:.0f}, détection fiable"
    else:
        state, reason = DEGRADED, f"{REASONS[DEGRADED]} (luminosité {brightness:.0f})"
    _insert(None, None, None, state, reason)
    print(f"[EVENT] vision = {vision_state} (luminosite {brightness:.0f})")
