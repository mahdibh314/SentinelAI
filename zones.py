"""Définition des zones. Coordonnées normalisées (0..1), indépendantes de la résolution."""
import cv2
import numpy as np

# name : nom affiché | allowed : zone autorisée ou non | polygon : points (x, y) normalisés
ZONES = [
    {"name": "zone_libre", "allowed": True,
     "polygon": [(0.0, 0.0), (0.48, 0.0), (0.48, 1.0), (0.0, 1.0)]},
    {"name": "zone_interdite", "allowed": False,
     "polygon": [(0.52, 0.0), (1.0, 0.0), (1.0, 1.0), (0.52, 1.0)]},
]


def to_pixels(polygon, width, height):
    """Convertit un polygone normalisé en pixels."""
    return np.array([(int(x * width), int(y * height)) for x, y in polygon], dtype=np.int32)


def find_zone(point, zones_px):
    """Retourne la zone qui contient le point (x, y), ou None si hors de toute zone."""
    px, py = float(point[0]), float(point[1])
    for zone in zones_px:
        if cv2.pointPolygonTest(zone["points"], (px, py), False) >= 0:
            return zone
    return None
