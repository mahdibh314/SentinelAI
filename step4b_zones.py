"""Étape 4b : zone confirmée avec temporisation. Quitter avec 'q' ou la croix."""
import sys
import time

import cv2
import torch
from ultralytics import YOLO

from step3_track import MODEL_NAME, CONFIDENCE, PERSON_CLASS, TRACKER, color_for_id
from step4_zones import build_zones_px, draw_zones, FONT
from zones import find_zone
from zone_state import ZoneTracker

WINDOW = "SentinelAI - zones (temporisation)"
CONFIRM_SECONDS = 0.7  # délai avant de confirmer un changement de zone


def draw_person(frame, box, zones_px, zone_tracker, now):
    """Dessine la personne avec sa zone confirmée (et la zone en attente si elle diffère)."""
    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
    track_id = int(box.id[0]) if box.id is not None else None

    foot = ((x1 + x2) / 2, float(y2))  # point au sol
    zone = find_zone(foot, zones_px)
    raw_name = zone["name"] if zone else "hors zone"

    if track_id is None:  # pas d'ID : pas de temporisation possible
        label, color = f"ID ? | {raw_name}", (128, 128, 128)
    else:
        confirmed, changed = zone_tracker.update(track_id, raw_name, now)
        if changed:
            print(f"ID {track_id} -> {confirmed} (confirmé)")
        label = f"ID {track_id} | {confirmed}"
        if raw_name != confirmed:
            label += f"  (-> {raw_name} ?)"
        color = color_for_id(track_id)

    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    cv2.circle(frame, (int(foot[0]), y2), 6, color, -1)
    cv2.putText(frame, label, (x1, max(y1 - 8, 15)), FONT, 0.5, color, 2)


def main(camera_index: int = 0) -> int:
    device = 0 if torch.cuda.is_available() else "cpu"
    print(f"Périphérique d'inférence : {device}")
    model = YOLO(MODEL_NAME)

    cap = cv2.VideoCapture(camera_index, cv2.CAP_V4L2)
    if not cap.isOpened():
        print(f"Erreur : impossible d'ouvrir la caméra d'index {camera_index}.")
        return 1

    zones_px = None
    zone_tracker = ZoneTracker(CONFIRM_SECONDS)
    fps = 0.0
    last = time.perf_counter()
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

            result = model.track(frame, persist=True, tracker=TRACKER,
                                 classes=[PERSON_CLASS], conf=CONFIDENCE,
                                 device=device, verbose=False)[0]

            now = time.perf_counter()
            frame = draw_zones(frame, zones_px)
            for box in result.boxes:
                draw_person(frame, box, zones_px, zone_tracker, now)

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
