"""Étape 1 : afficher le flux de la webcam. Quitter avec 'q' ou en fermant la fenêtre."""
import sys

import cv2

WINDOW = "SentinelAI - camera"


def main(camera_index: int = 0) -> int:
    cap = cv2.VideoCapture(camera_index, cv2.CAP_V4L2)
    if not cap.isOpened():
        print(f"Erreur : impossible d'ouvrir la caméra d'index {camera_index}.")
        print("Vérifie : /dev/video*, une autre application qui l'utilise, ou essaie un autre index.")
        return 1

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Erreur : lecture d'une image impossible (caméra déconnectée ?).")
                return 1

            cv2.imshow(WINDOW, frame)

            # 'q' pour quitter
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            # Fermeture par la croix de la fenêtre
            if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    sys.exit(main(index))
