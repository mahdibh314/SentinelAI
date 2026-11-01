#!/usr/bin/env python3
"""Script de vérification de l'environnement matériel et logiciel SentinelAI."""

import os
import sys
import sqlite3
from pathlib import Path

# Couleurs ANSI
C_GREEN = "\033[92m"
C_RED = "\033[91m"
C_YELLOW = "\033[93m"
C_BLUE = "\033[94m"
C_BOLD = "\033[1m"
C_RESET = "\033[0m"

def print_result(label: str, status: str, details: str = ""):
    if status == "OK":
        badge = f"{C_GREEN}[ OK ]{C_RESET}"
    elif status == "AVERTISSEMENT":
        badge = f"{C_YELLOW}[ WARN ]{C_RESET}"
    else:
        badge = f"{C_RED}[ KO ]{C_RESET}"
    print(f" {badge:16} {C_BOLD}{label:20}{C_RESET} : {details}")

def main():
    print(f"\n{C_BLUE}{C_BOLD}=== Diagnostic SentinelAI (deploy check) ==={C_RESET}\n")

    base_dir = Path(__file__).resolve().parent.parent
    all_ok = True

    # 1. GPU / CUDA
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            vram_mb = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)
            print_result("GPU (CUDA)", "OK", f"{gpu_name} ({vram_mb:.0f} Mo VRAM, cu130)")
        else:
            all_ok = False
            print_result("GPU (CUDA)", "KO", "CUDA non disponible dans PyTorch")
    except Exception as e:
        all_ok = False
        print_result("GPU (CUDA)", "KO", f"Erreur import torch : {e}")

    # 2. Webcam
    camera_idx = int(os.environ.get("CAMERA_INDEX", 0))
    video_dev = f"/dev/video{camera_idx}"
    if not os.path.exists(video_dev):
        all_ok = False
        print_result("Webcam", "KO", f"{video_dev} introuvable")
    else:
        try:
            import cv2
            cap = cv2.VideoCapture(camera_idx, cv2.CAP_V4L2)
            if cap.isOpened():
                ret, _ = cap.read()
                cap.release()
                if ret:
                    print_result("Webcam", "OK", f"{video_dev} accessible et capture fonctionnelle")
                else:
                    print_result("Webcam", "AVERTISSEMENT", f"{video_dev} ouvert mais aucune image reçue")
            else:
                all_ok = False
                print_result("Webcam", "KO", f"Impossible d'ouvrir {video_dev}")
        except Exception as e:
            all_ok = False
            print_result("Webcam", "KO", f"Erreur OpenCV : {e}")

    # 3. ESP32-S3 Serial
    serial_port = os.environ.get("SERIAL_PORT", "/dev/ttyACM0")
    if os.path.exists(serial_port):
        # Vérification permissions lecture/écriture
        if os.access(serial_port, os.R_OK | os.W_OK):
            print_result("ESP32-S3", "OK", f"Connecté sur {serial_port} (droits r/w OK)")
        else:
            all_ok = False
            print_result("ESP32-S3", "KO", f"{serial_port} présent mais droits d'accès insuffisants (groupe dialout requis)")
    else:
        all_ok = False
        print_result("ESP32-S3", "KO", f"Périphérique {serial_port} non détecté (branchez l'ESP32 en USB)")

    # 4. Lecteur de code (evdev / HID)
    try:
        import evdev
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        scanner_found = None
        for dev in devices:
            name_lower = dev.name.lower()
            if any(k in name_lower for k in ["barcode", "scanner", "reader", "hid", "keyboard"]):
                scanner_found = dev
                break
        if scanner_found:
            print_result("Lecteur Code", "OK", f"Périphérique détecté : {scanner_found.name} ({scanner_found.path})")
        else:
            print_result("Lecteur Code", "AVERTISSEMENT", "Aucun scanner USB dédié détecté (repli sur saisie clavier/stdin)")
    except Exception as e:
        print_result("Lecteur Code", "AVERTISSEMENT", f"evdev non fonctionnel ({e}) - repli stdin")

    # 5. Agent micro-ROS
    agent_path = Path("/home/mahdi/microros_ws/install/micro_ros_agent/lib/micro_ros_agent/micro_ros_agent")
    if agent_path.is_file() and os.access(agent_path, os.X_OK):
        print_result("Agent micro-ROS", "OK", f"Installé ({agent_path})")
    else:
        # Vérifier si disponible dans le PATH
        import shutil
        if shutil.which("micro_ros_agent"):
            print_result("Agent micro-ROS", "OK", "Disponible dans le PATH")
        else:
            all_ok = False
            print_result("Agent micro-ROS", "KO", "micro_ros_agent non trouvé (exécutez ./deploy install)")

    # 6. Modèle YOLO11n
    model_path = base_dir / os.environ.get("YOLO_MODEL", "yolo11n.pt")
    if model_path.is_file():
        size_mb = model_path.stat().st_size / (1024 * 1024)
        print_result("Modèle YOLO", "OK", f"{model_path.name} présent ({size_mb:.1f} Mo)")
    else:
        all_ok = False
        print_result("Modèle YOLO", "KO", f"{model_path} introuvable")

    # 7. Base de données SQLite
    db_path = base_dir / os.environ.get("DB_PATH", "data/sentinel.db")
    if db_path.is_file():
        try:
            with sqlite3.connect(db_path) as con:
                cur = con.cursor()
                cur.execute("SELECT COUNT(*) FROM users")
                n_users = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM events")
                n_events = cur.fetchone()[0]
            print_result("Base SQLite", "OK", f"{db_path.name} ({n_users} utilisateur(s), {n_events} événement(s))")
        except Exception as e:
            all_ok = False
            print_result("Base SQLite", "KO", f"Erreur lecture SQLite : {e}")
    else:
        all_ok = False
        print_result("Base SQLite", "KO", f"{db_path} absent (exécutez scripts/seed_db.py)")

    print()
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
