"""Étape 4a : zones d'intérêt + zone de chaque personne suivie. Quitter avec 'q' ou la croix."""
import sys
import time

import cv2
import torch
from ultralytics import YOLO

from step3_track import MODEL_NAME, CONFIDENCE, PERSON_CLASS, TRACKER, color_for_id
from zones import ZONES, to_pixels, find_zone

WINDOW = "SentinelAI - zones"
FONT = cv2.FONT_HERSHEY_SIMPLEX
GREEN, RED = (0, 200, 0), (0, 0, 255)


def build_zones_px(width, height):
    """Prépare les zones en pixels, avec une couleur selon l'autorisation."""
    return [{"name": z["name"], "allowed": z["allowed"],
             "points": to_pixels(z["polygon"], width, height),
             "color": GREEN if z["allowed"] else RED} for z in ZONES]


def draw_zones(frame, zones_px):
    """Remplit les zones en transparence, puis trace leur contour et leur nom."""
    overlay = frame.copy()
    for z in zones_px:
        cv2.fillPoly(overlay, [z["points"]], z["color"])
    frame = cv2.addWeighted(overlay, 0.25, frame, 0.75, 0)
    for z in zones_px:
        cv2.polylines(frame, [z["points"]], True, z["color"], 2)
        x, y = z["points"][0]
        cv2.putText(frame, z["name"], (int(x) + 5, int(y) + 45), FONT, 0.6, z["color"], 2)
    return frame


def draw_person(frame, box, zones_px, last_zone):
    """Dessine la personne, son ID et sa zone. Affiche dans le terminal les changements de zone."""
    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
    track_id = int(box.id[0]) if box.id is not None else None

    foot = ((x1 + x2) / 2, float(y2))  # point au sol : milieu du bord bas de la boîte
    zone = find_zone(foot, zones_px)
    zone_name = zone["name"] if zone else "hors zone"

    color = color_for_id(track_id) if track_id is not None else (128, 128, 128)
    id_text = track_id if track_id is not None else "?"
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    cv2.circle(frame, (int(foot[0]), y2), 6, color, -1)
    cv2.putText(frame, f"ID {id_text} | {zone_name}", (x1, max(y1 - 8, 15)), FONT, 0.5, color, 2)

    if track_id is not None and last_zone.get(track_id) != zone_name:
        print(f"ID {track_id} -> {zone_name}")
        last_zone[track_id] = zone_name


def main(camera_index: int = 0) -> int:
    device = 0 if torch.cuda.is_available() else "cpu"
    print(f"Périphérique d'inférence : {device}")
    model = YOLO(MODEL_NAME)

    cap = cv2.VideoCapture(camera_index, cv2.CAP_V4L2)
    if not cap.isOpened():
        print(f"Erreur : impossible d'ouvrir la caméra d'index {camera_index}.")
        return 1

    zones_px = None
    last_zone = {}
    fps = 0.0
    last = time.perf_counter()
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Erreur : lecture d'une image impossible.")
                return 1

            if zones_px is None:  # on connaît la taille de l'image à la première lecture
                height, width = frame.shape[:2]
                zones_px = build_zones_px(width, height)
                print(f"Image : {width}x{height}")

            result = model.track(frame, persist=True, tracker=TRACKER,
                                 classes=[PERSON_CLASS], conf=CONFIDENCE,
                                 device=device, verbose=False)[0]

            frame = draw_zones(frame, zones_px)
            for box in result.boxes:
                draw_person(frame, box, zones_px, last_zone)

            now = time.perf_counter()
            fps = 0.9 * fps + 0.1 * (1.0 / (now - last))
            last = now
            info = f"FPS: {fps:.1f} | inference: {result.speed['inference']:.1f} ms | personnes: {len(result.boxes)}"
            cv2.putText(frame, info, (10, 25), FONT, 0.6, (0, 255, 255), 2)

            cv2.imshow(WINDOW, frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    sys.exit(main(index))
