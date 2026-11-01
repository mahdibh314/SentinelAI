"""Scanner node for SentinelAI.

Lit les codes depuis :
1. Un lecteur code-barres / QR USB HID via evdev (avec capture exclusive grab)
2. Saisie interactive terminal (repli laptop / tests)
Publie le code brut sur /scan/code (std_msgs/String).
"""

import os
import sys
import threading
import select
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

KEY_MAP = {
    "KEY_0": "0", "KEY_1": "1", "KEY_2": "2", "KEY_3": "3", "KEY_4": "4",
    "KEY_5": "5", "KEY_6": "6", "KEY_7": "7", "KEY_8": "8", "KEY_9": "9",
    "KEY_A": "a", "KEY_B": "b", "KEY_C": "c", "KEY_D": "d", "KEY_E": "e",
    "KEY_F": "f", "KEY_G": "g", "KEY_H": "h", "KEY_I": "i", "KEY_J": "j",
    "KEY_K": "k", "KEY_L": "l", "KEY_M": "m", "KEY_N": "n", "KEY_O": "o",
    "KEY_P": "p", "KEY_Q": "q", "KEY_R": "r", "KEY_S": "s", "KEY_T": "t",
    "KEY_U": "u", "KEY_V": "v", "KEY_W": "w", "KEY_X": "x", "KEY_Y": "y",
    "KEY_Z": "z", "KEY_MINUS": "-", "KEY_UNDERSCORE": "_", "KEY_SLASH": "/",
    "KEY_SPACE": " ", "KEY_DOT": ".", "KEY_COMMA": ","
}

class ScannerNode(Node):
    def __init__(self):
        super().__init__('scanner_node')
        self.publisher_ = self.create_publisher(String, '/scan/code', 10)
        
        self.device_name = self.declare_parameter('device_name', '').value
        self.running = True

        self.get_logger().info('Démarrage du scanner_node...')

        # Lancer le thread de lecture evdev si disponible
        self.evdev_thread = threading.Thread(target=self._run_evdev, daemon=True)
        self.evdev_thread.start()

        # Lancer le thread de repli stdin (pour utilisation directe sur le laptop)
        self.stdin_thread = threading.Thread(target=self._run_stdin, daemon=True)
        self.stdin_thread.start()

    def publish_code(self, code: str):
        code = code.strip()
        if not code:
            return
        msg = String()
        msg.data = code
        self.publisher_.publish(msg)
        self.get_logger().info(f'Code scanné publié : {code}')

    def _find_evdev_device(self):
        try:
            import evdev
            devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
            for dev in devices:
                # Si un nom spécifique est configuré
                if self.device_name and self.device_name.lower() in dev.name.lower():
                    return dev
                # Sinon détection automatique de lecteur code-barres / scanner
                name_l = dev.name.lower()
                if any(k in name_l for k in ["barcode", "scanner", "reader"]):
                    return dev
            return None
        except Exception as e:
            self.get_logger().warning(f'Impossible de lister evdev : {e}')
            return None

    def _run_evdev(self):
        try:
            import evdev
            from evdev import ecodes
        except ImportError:
            self.get_logger().warning("Module evdev non installé, mode USB HID désactivé.")
            return

        device = self._find_evdev_device()
        if not device:
            self.get_logger().info("Aucun scanner USB HID dédié trouvé. Utilisation de l'entrée clavier standard (laptop/stdin).")
            return

        self.get_logger().info(f"Scanner USB HID connecté : {device.name} ({device.path}). Mode grab actif.")
        try:
            device.grab()
        except Exception as e:
            self.get_logger().warning(f"Impossible de verrouiller le scanner (grab) : {e}")

        buffer = []
        try:
            for event in device.read_loop():
                if not self.running:
                    break
                if event.type == ecodes.EV_KEY and event.value == 1:  # Touche enfoncée
                    key_name = ecodes.KEY[event.code]
                    if key_name in ("KEY_ENTER", "KEY_KPENTER"):
                        code = "".join(buffer)
                        buffer.clear()
                        self.publish_code(code)
                    elif key_name == "KEY_BACKSPACE":
                        if buffer:
                            buffer.pop()
                    else:
                        ch = KEY_MAP.get(key_name)
                        if ch:
                            buffer.append(ch)
        except Exception as e:
            self.get_logger().error(f"Erreur boucle evdev : {e}")
        finally:
            try:
                device.ungrab()
            except Exception:
                pass

    def _run_stdin(self):
        """Thread de repli pour saisie manuelle au clavier (laptop) sans bloquer."""
        self.get_logger().info("Écoute stdin active : vous pouvez aussi taper un code dans le terminal et appuyer sur Entrée.")
        while self.running and rclpy.ok():
            try:
                # Vérifier si stdin est disponible et interactif
                if not sys.stdin or sys.stdin.closed:
                    break
                rlist, _, _ = select.select([sys.stdin], [], [], 1.0)
                if rlist:
                    line = sys.stdin.readline()
                    if line:
                        self.publish_code(line.strip())
            except Exception:
                break

    def destroy_node(self):
        self.running = False
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = ScannerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
