"""Étape 2b : détection de personnes avec YOLO. Quitter avec 'q' ou en fermant la fenêtre."""
import sys
import time

import cv2
import torch
from ultralytics import YOLO

WINDOW = "SentinelAI - detection"
MODEL_NAME = "yolo11n.pt"  # modèle léger officiel
CONFIDENCE = 0.5           # seuil de confiance minimal
PERSON_CLASS = 0           # classe "person" dans COCO
GREEN = (0, 200, 0)


def draw_person(frame, box):
    """Dessine une boîte et le score de confiance pour une personne détectée."""
    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
    score = float(box.conf[0])
    cv2.rectangle(frame, (x1, y1), (x2, y2), GREEN, 2)
    cv2.putText(frame, f"person {score:.2f}", (x1, max(y1 - 8, 15)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, GREEN, 2)


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

            result = model.predict(frame, classes=[PERSON_CLASS], conf=CONFIDENCE,
                                   device=device, verbose=False)[0]
            for box in result.boxes:
                draw_person(frame, box)

            # FPS lissé et temps d'inférence du modèle (ms)
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
