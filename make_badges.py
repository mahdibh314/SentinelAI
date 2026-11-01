"""Génère des badges QR de test (identifiants opaques, aucune donnée personnelle)."""
from pathlib import Path

import qrcode

BADGES = ["user_demo", "user_admin", "badge_inconnu"]

out = Path("badges")
out.mkdir(exist_ok=True)
for badge_id in BADGES:
    path = out / f"{badge_id}.png"
    qrcode.make(badge_id, box_size=10, border=4).save(path)
    print("créé :", path)
