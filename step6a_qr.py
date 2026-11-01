"""Étape 6a : lecture d'un badge QR et vérification de l'identifiant. Quitter : 'q' ou la croix."""
import sys
import time

import cv2

from access_rules import ACCESS_RIGHTS

WINDOW = "SentinelAI - lecture QR"
FONT = cv2.FONT_HERSHEY_SIMPLEX
GONE_AFTER_S = 1.0  # le QR est considéré parti après 1 s sans lecture


def main(camera_index: int = 0) -> int:
    cap = cv2.VideoCapture(camera_index, cv2.CAP_V4L2)
    if not cap.isOpened():
        print(f"Erreur : impossible d'ouvrir la caméra d'index {camera_index}.")
        return 1

    detector = cv2.QRCodeDetector()
    last_value, last_seen = None, 0.0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Erreur : lecture d'une image impossible.")
                return 1

            data, points, _ = detector.detectAndDecode(frame)
            now = time.perf_counter()

            if points is not None:  # un QR est localisé (même s'il n'est pas lisible)
                pts = points.astype(int).reshape(-1, 2)
                known = data in ACCESS_RIGHTS
                color = (0, 200, 0) if known else (0, 0, 255)
                cv2.polylines(frame, [pts], True, color, 3)
                if data:
                    status = "connu" if known else "INCONNU"
                    cv2.putText(frame, f"{data} ({status})", (int(pts[0][0]), max(int(pts[0][1]) - 10, 20)),
                                FONT, 0.7, color, 2)

            if data:
                if data != last_value:  # on n'affiche que les nouvelles lectures
                    status = "connu" if data in ACCESS_RIGHTS else "inconnu"
                    print(f"QR lu : {data!r} -> badge {status}")
                    last_value = data
                last_seen = now
            elif last_value is not None and now - last_seen > GONE_AFTER_S:
                print("QR disparu")
                last_value = None

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
