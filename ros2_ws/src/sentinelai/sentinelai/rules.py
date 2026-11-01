"""Règles d'accès pour SentinelAI.

Converti et adapté pour ROS 2 et la base de données SQLite.
"""

ZONE_POLICY = {
    "zone_libre": "open",
    "zone_interdite": "restricted",
}

AUTHORIZED = "autorisé"
FORBIDDEN = "présence interdite"
UNCONFIRMED = "identité non confirmée"
DEGRADED = "vision dégradée"

def check_access(user_record: dict | None, target_zone: str = "zone_interdite") -> tuple[bool, str]:
    """Vérifie si un utilisateur est autorisé pour une zone donnée.

    Args:
        user_record: Dict contenant les infos utilisateur ou None si inconnu.
        target_zone: Nom de la zone demandée.

    Returns:
        (is_granted: bool, reason: str)
    """
    if not user_record:
        return False, "Code inconnu ou non enregistré"
    
    if not user_record.get("active", 1):
        return False, "Utilisateur inactif / suspendu"

    user_zone = user_record.get("zone", "zone_libre")
    level = user_record.get("level", 1)

    # Si la zone cible est ouverte à tous
    if ZONE_POLICY.get(target_zone, "open") == "open":
        return True, "Zone libre d'accès"

    # Zone restreinte : vérification des droits
    if target_zone == "zone_interdite":
        if user_zone == "zone_interdite" or level >= 2:
            return True, "Accès autorisé (niveau/zone valide)"
        return False, "Droits insuffisants pour la zone restreinte"

    return True, "Accès autorisé"
