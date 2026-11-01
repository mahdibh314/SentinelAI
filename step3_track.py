"""Étape 3 : détection + suivi de personnes (ByteTrack via Ultralytics). Quitter avec 'q' ou la croix."""
import sys
import time

import cv2
import torch
from ultralytics import YOLO

WINDOW = "SentinelAI - tracking"
MODEL_NAME = "yolo11n.pt"
CONFIDENCE = 0.25
PERSON_CLASS = 0
TRACKER = "bytetrack.yaml"


def color_for_id(track_id: int):
    """Couleur stable par ID, pour distinguer visuellement les personnes."""
    palette = [(0, 200, 0), (255, 128, 0), (0, 128, 255), (200, 0, 200),
               (0, 200, 200), (255, 255, 0), (128, 128, 255), (0, 255, 128)]
    return palette[track_id % len(palette)]


def draw_tracked_person(frame, box):
    """Dessine la boîte, l'ID de suivi et le score. L'ID peut être absent (None)."""
    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
    score = float(box.conf[0])
    track_id = int(box.id[0]) if box.id is not None else None

    color = color_for_id(track_id) if track_id is not None else (128, 128, 128)
    label = f"ID {track_id}" if track_id is not None else "ID ?"
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    cv2.putText(frame, f"{label} ({score:.2f})", (x1, max(y1 - 8, 15)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)


def main(camera_index: int = 0) -> int:
    device = 0 if torch.cuda.is_available() else "cpu"
    print(f"Périphérique d'inférence : {device}")
    model = YOLO(MODEL_NAME)

    cap = cv2.VideoCapture(camera_index, cv2.CAP_V4L2)
    if not cap.isOpened():
        print(f"Erreur : impossible d'ouvrir la caméra d'index {camera_index}.")
        return 1

    fps = 0.0
    last = time.perf_counter()
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Erreur : lecture d'une image impossible.")
                return 1

            # persist=True : garder la mémoire du suivi d'une image à l'autre
            result = model.track(frame, persist=True, tracker=TRACKER,
                                 classes=[PERSON_CLASS], conf=CONFIDENCE,
                                 device=device, verbose=False)[0]
            for box in result.boxes:
                draw_tracked_person(frame, box)

            now = time.perf_counter()
            fps = 0.9 * fps + 0.1 * (1.0 / (now - last))
            last = now
            info = (f"FPS: {fps:.1f} | inference: {result.speed['inference']:.1f} ms "
                    f"| personnes: {len(result.boxes)}")
            cv2.putText(frame, info, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

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