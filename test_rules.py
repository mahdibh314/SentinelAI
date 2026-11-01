"""Test des règles d'accès sans caméra."""
from access_rules import decide_state, AUTHORIZED, FORBIDDEN, UNCONFIRMED, DEGRADED

CASES = [
    ("zone_libre", None, True, AUTHORIZED),
    ("hors zone", None, True, AUTHORIZED),
    ("zone_interdite", None, True, UNCONFIRMED),
    ("zone_interdite", "badge_inconnu", True, UNCONFIRMED),
    ("zone_interdite", "user_demo", True, FORBIDDEN),
    ("zone_interdite", "user_admin", True, AUTHORIZED),
    ("zone_interdite", "user_admin", False, DEGRADED),
    ("zone_libre", None, False, DEGRADED),
]

failures = 0
for zone, user, vision_ok, expected in CASES:
    got = decide_state(zone, user, vision_ok)
    ok = got == expected
    failures += not ok
    print(("OK    " if ok else "ECHEC ") + f"{zone:15} badge={user!s:14} vision={vision_ok!s:5} -> {got}")
print("tests OK" if failures == 0 else f"{failures} échec(s)")
