#!/usr/bin/env python3
"""Générateur de QR codes de badges de test pour SentinelAI."""

from pathlib import Path
import qrcode

BADGES = ["user_demo", "user_admin", "user_guest", "badge_inconnu"]

def make_badges(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    for badge_id in BADGES:
        path = output_dir / f"{badge_id}.png"
        img = qrcode.make(badge_id, box_size=10, border=4)
        img.save(path)
        print(f"Badge généré : {path}")

if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "badges"
    make_badges(out)
