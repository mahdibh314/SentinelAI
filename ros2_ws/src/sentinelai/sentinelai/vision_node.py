"""Vision node for SentinelAI.

- Maintient la capture vidéo de la caméra (index configurable : laptop ou extension USB)
- Conserve la dernière image en mémoire sans écrire de vidéo sur disque
- Sur réception d'un événement d'accès refusé (status="denied") sur /access/result :
  - Déclenche l'inférence YOLO11n (classe person=0)
  - Compte le nombre d'intrus
  - Sauvegarde l'image annotée dans data/snapshots/intrusion_<timestamp>.jpg
  - Publie le résultat sur /intrusion/info (JSON)
- Fournit la dernière image encodée en JPEG pour le flux live web
"""

import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path

import cv2
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class VisionNode(Node):
    # Image partagée en mémoire pour le streaming web
    latest_jpeg = None
    latest_jpeg_lock = threading.Lock()

    def __init__(self):
        super().__init__('vision_node')

        # Paramètres configurables
        self.declare_parameter('camera_index', int(os.environ.get('CAMERA_INDEX', 0)))
        self.declare_parameter('confidence', float(os.environ.get('YOLO_CONF', 0.25)))
        self.declare_parameter('model_path', os.environ.get('YOLO_MODEL', 'yolo11n.pt'))
        self.declare_parameter('snapshot_dir', os.environ.get('SNAPSHOT_DIR', 'data/snapshots'))

        self.camera_index = self.get_parameter('camera_index').value
        self.confidence = self.get_parameter('confidence').value
        self.model_path = self.get_parameter('model_path').value
        self.snapshot_dir = Path(self.get_parameter('snapshot_dir').value)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

        # Abonnements et publications
        self.access_sub = self.create_subscription(String, '/access/result', self.on_access_result, 10)
        self.intrusion_pub = self.create_publisher(String, '/intrusion/info', 10)

        # Chargement du modèle YOLO (une seule fois hors chemin critique)
        self.get_logger().info(f"Chargement du modèle YOLO ({self.model_path})...")
        from ultralytics import YOLO
        import torch
        device = 0 if torch.cuda.is_available() else "cpu"
        self.model = YOLO(self.model_path)
        self.device = device
        self.get_logger().info(f"Modèle YOLO prêt sur périphérique : {device}")

        # Boucle de capture caméra
        self.running = True
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()

    def _capture_loop(self):
        """Boucle dédiée à la capture continue des images de la webcam."""
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_V4L2)
        if not cap.isOpened():
            # Repli sur backend standard si CAP_V4L2 échoue
            cap = cv2.VideoCapture(self.camera_index)

        if not cap.isOpened():
            self.get_logger().error(f"Impossible d'ouvrir la caméra index={self.camera_index}")
            return

        self.get_logger().info(f"Caméra index={self.camera_index} ouverte avec succès.")

        while self.running and rclpy.ok():
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            with self.frame_lock:
                self.current_frame = frame.copy()

            # Mise à jour du JPEG pour le flux live web
            try:
                ret_enc, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                if ret_enc:
                    with VisionNode.latest_jpeg_lock:
                        VisionNode.latest_jpeg = buffer.tobytes()
            except Exception:
                pass

            time.sleep(0.03)  # ~30 FPS

        cap.release()

    def on_access_result(self, msg: String):
        """Réception d'un résultat d'accès."""
        try:
            data = json.loads(msg.data)
        except Exception as e:
            self.get_logger().error(f"Format JSON invalide dans /access/result : {e}")
            return

        # Si l'accès est refusé, analyse d'intrusion
        if data.get("status") == "denied":
            self.get_logger().warning("Accès REFUSÉ détecté : analyse de sécurité et capture snapshot...")
            threading.Thread(target=self._process_intrusion, args=(data,), daemon=True).start()

    def _process_intrusion(self, access_data: dict):
        frame_to_process = None
        with self.frame_lock:
            if self.current_frame is not None:
                frame_to_process = self.current_frame.copy()

        if frame_to_process is None:
            self.get_logger().error("Aucune image disponible pour l'analyse d'intrusion.")
            return

        now = datetime.now()
        ts_str = now.strftime("%Y%m%d_%H%M%S")
        iso_ts = now.isoformat(timespec="seconds")

        # Inférence YOLO11n (classe 0 = person)
        results = self.model(
            frame_to_process,
            classes=[0],
            conf=self.confidence,
            device=self.device,
            verbose=False
        )

        n_persons = 0
        annotated_frame = frame_to_process.copy()

        if results and len(results) > 0:
            boxes = results[0].boxes
            n_persons = len(boxes)
            # Annotation sur l'image
            annotated_frame = results[0].plot()

        # Horodatage et texte de sécurité sur l'image
        banner_text = f"REFUS ACCES - {iso_ts} - {n_persons} personne(s)"
        cv2.putText(annotated_frame, banner_text, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        # Sauvegarde du snapshot JPG annoté
        filename = f"intrusion_{ts_str}_{access_data.get('code_id', 'unknown')}.jpg"
        filepath = self.snapshot_dir / filename
        cv2.imwrite(str(filepath), annotated_frame)
        self.get_logger().info(f"Capture sauvegardée : {filepath} ({n_persons} personne(s) détectée(s))")

        # Publication sur /intrusion/info
        info_payload = {
            "ts": iso_ts,
            "event_id": access_data.get("event_id"),
            "code_id": access_data.get("code_id"),
            "persons": n_persons,
            "snapshot": str(filepath.relative_to(Path.cwd()))
        }
        info_msg = String()
        info_msg.data = json.dumps(info_payload)
        self.intrusion_pub.publish(info_msg)

    def destroy_node(self):
        self.running = False
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = VisionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
