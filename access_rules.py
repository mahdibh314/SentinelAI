"""Règles d'accès : politique des zones, droits de test et état d'une personne."""

# "open" : accessible à tous | "restricted" : badge avec droit requis
ZONE_POLICY = {
    "zone_libre": "open",
    "zone_interdite": "restricted",
}

# Droits de test : identifiants opaques, aucune donnée personnelle
ACCESS_RIGHTS = {
    "user_demo": {"zone_libre"},
    "user_admin": {"zone_libre", "zone_interdite"},
}

AUTHORIZED = "autorisé"
FORBIDDEN = "présence interdite"
UNCONFIRMED = "identité non confirmée"
DEGRADED = "vision dégradée"


def decide_state(zone_name, user_id, vision_ok):
    """Retourne l'état d'une personne selon sa zone, son badge (ou None) et la qualité de la vision."""
    if not vision_ok:
        return DEGRADED
    if ZONE_POLICY.get(zone_name, "open") == "open":  # "hors zone" : pas de restriction
        return AUTHORIZED
    if user_id not in ACCESS_RIGHTS:  # pas de badge ou badge inconnu
        return UNCONFIRMED
    return AUTHORIZED if zone_name in ACCESS_RIGHTS[user_id] else FORBIDDEN
