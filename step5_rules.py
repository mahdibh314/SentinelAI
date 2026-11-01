"""Étape 5 : règles d'accès avec événements temporisés. Badges simulés au clavier. Quitter : 'q' ou la croix."""
import sys
import time

import cv2
import torch
from ultralytics import YOLO

from access_rules import AUTHORIZED, FORBIDDEN, UNCONFIRMED, DEGRADED, decide_state
from step3_track import MODEL_NAME, CONFIDENCE, PERSON_CLASS, TRACKER
from step4_zones import build_zones_px, draw_zones, FONT
from zones import find_zone
from zone_state import ZoneTracker  # réutilisé : confirme une valeur après un délai stable

WINDOW = "SentinelAI - regles d'acces"
BRIGHTNESS_MIN = 40.0   # luminosité moyenne (0-255) sous laquelle la vision est jugée dégradée
ZONE_CONFIRM_S = 0.7
STATE_CONFIRM_S = 0.5   # un changement d'état doit rester stable 1,5 s pour devenir un événement
VISION_CONFIRM_S = 1.0
BADGE_KEYS = {ord("1"): "user_demo", ord("2"): "user_admin"}

# Textes ASCII pour l'écran (les polices OpenCV n'affichent pas les accents)
DISPLAY = {AUTHORIZED: "AUTORISE", FORBIDDEN: "PRESENCE INTERDITE",
           UNCONFIRMED: "IDENTITE NON CONFIRMEE", DEGRADED: "VISION DEGRADEE"}
STATE_COLORS = {AUTHORIZED: (0, 200, 0), FORBIDDEN: (0, 0, 255),
                UNCONFIRMED: (0, 165, 255), DEGRADED: (160, 160, 160)}


def draw_person(frame, box, zones_px, zone_tracker, state_tracker, badges, vision_ok, now):
    """Calcule l'état de la personne, l'affiche, et signale les changements d'état confirmés."""
    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
    track_id = int(box.id[0]) if box.id is not None else None

    if track_id is None:  # pas d'ID confirmé : pas de décision possible
        cv2.rectangle(frame, (x1, y1), (x2, y2), (128, 128, 128), 2)
        cv2.putText(frame, "ID ? (suivi non confirme)", (x1, max(y1 - 8, 15)), FONT, 0.5, (128, 128, 128), 2)
        return

    foot = ((x1 + x2) / 2, float(y2))  # point au sol
    zone = find_zone(foot, zones_px)
    zone_name, _ = zone_tracker.update(track_id, zone["name"] if zone else "hors zone", now)

    user = badges.get(track_id)
    state, changed = state_tracker.update(track_id, decide_state(zone_name, user, vision_ok), now)
    if changed:
        print(f"[EVENT] ID {track_id} | zone={zone_name} | badge={user or 'aucun'} | etat={state}")

    color = STATE_COLORS[state]
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    cv2.circle(frame, (int(foot[0]), y2), 6, color, -1)
    cv2.putText(frame, f"ID {track_id} | {zone_name} | {user or 'sans badge'}",
                (x1, max(y1 - 28, 15)), FONT, 0.5, color, 2)
    cv2.putText(frame, DISPLAY[state], (x1, max(y1 - 8, 15)), FONT, 0.6, color, 2)


def handle_keys(key, result, badges):
    """Badges simulés : 1 = user_demo, 2 = user_admin, 0 = effacer. Un badge exige exactement une personne suivie."""
    if key == ord("0"):
        badges.clear()
        print("Badges effacés")
    elif key in BADGE_KEYS:
        ids = [int(b.id[0]) for b in result.boxes if b.id is not None]
        if len(result.boxes) == 1 and len(ids) == 1:
            badges[ids[0]] = BADGE_KEYS[key]
            print(f"Badge {BADGE_KEYS[key]} associé à l'ID {ids[0]}")
        else:
            print(f"Badge refusé : {len(result.boxes)} personne(s) détectée(s), il en faut exactement une "
                  f"avec un ID confirmé -> identité non confirmée")


def main(camera_index: int = 0) -> int:
    device = 0 if torch.cuda.is_available() else "cpu"
    print(f"Périphérique d'inférence : {device}")
    model = YOLO(MODEL_NAME)

    cap = cv2.VideoCapture(camera_index, cv2.CAP_V4L2)
    if not cap.isOpened():
        print(f"Erreur : impossible d'ouvrir la caméra d'index {camera_index}.")
        return 1

    zones_px = None
    badges = {}  # track_id -> identifiant de badge simulé
    zone_tracker = ZoneTracker(ZONE_CONFIRM_S)
    state_tracker = ZoneTracker(STATE_CONFIRM_S)
    vision_tracker = ZoneTracker(VISION_CONFIRM_S)
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Erreur : lecture d'une image impossible.")
                return 1

            if zones_px is None:
                height, width = frame.shape[:2]
                zones_px = build_zones_px(width, height)
                print(f"Image : {width}x{height}")

            # Qualité de la vision : luminosité moyenne de l'image brute
            brightness = float(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean())
            now = time.perf_counter()
            vision_state, vision_changed = vision_tracker.update(
                "camera", "ok" if brightness >= BRIGHTNESS_MIN else "degraded", now)
            if vision_changed:
                print(f"[EVENT] vision = {vision_state} (luminosite {brightness:.0f})")
            vision_ok = vision_state == "ok"

            result = model.track(frame, persist=True, tracker=TRACKER,
                                 classes=[PERSON_CLASS], conf=CONFIDENCE,
                                 device=device, verbose=False)[0]

            frame = draw_zones(frame, zones_px)
            for box in result.boxes:
                draw_person(frame, box, zones_px, zone_tracker, state_tracker, badges, vision_ok, now)

            cv2.putText(frame, f"Luminosite: {brightness:.0f} (min {BRIGHTNESS_MIN:.0f}) | vision: {vision_state}",
                        (10, height - 30), FONT, 0.5, (0, 255, 255), 2)
            cv2.putText(frame, "Badge simule : 1=user_demo 2=user_admin 0=aucun",
                        (10, height - 10), FONT, 0.5, (0, 255, 255), 2)

            cv2.imshow(WINDOW, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            handle_keys(key, result, badges)
            if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    sys.exit(main(index))
