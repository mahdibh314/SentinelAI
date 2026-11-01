"""Access node for SentinelAI.

- Reçoit les codes lus sur /scan/code
- Vérifie les droits dans la base de données SQLite
- Publie le résultat sur /access/result (JSON)
- Commande la LED verte (1) pour code valide (durant 5s)
- Commande la LED rouge (2) + buzzer (1) pour code invalide (jusqu'à /system/ack ou 10s max)
- Journalise les événements dans SQLite
"""

import json
import os
import threading
from datetime import datetime
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Int8, Empty

from sentinelai.db import get_user_by_code, log_event
from sentinelai.rules import check_access

class AccessNode(Node):
    def __init__(self):
        super().__init__('access_node')

        # Paramètres
        self.declare_parameter('valid_duration_s', 5.0)
        self.declare_parameter('alarm_max_s', 10.0)
        self.valid_duration_s = self.get_parameter('valid_duration_s').value
        self.alarm_max_s = self.get_parameter('alarm_max_s').value

        # Abonnements
        self.code_sub = self.create_subscription(String, '/scan/code', self.on_code_received, 10)
        self.ack_sub = self.create_subscription(Empty, '/system/ack', self.on_alarm_ack, 10)
        self.intrusion_sub = self.create_subscription(String, '/intrusion/info', self.on_intrusion_info, 10)

        # Publications
        self.result_pub = self.create_publisher(String, '/access/result', 10)
        self.led_pub = self.create_publisher(Int8, '/esp32/led_cmd', 10)
        self.buzzer_pub = self.create_publisher(Int8, '/esp32/buzzer_cmd', 10)

        # Timers et états
        self.active_timer = None
        self.latest_denied_event_id = None
        self.alarm_active = False

        self.get_logger().info('AccessNode initialisé et prêt.')

    def send_led_cmd(self, val: int):
        msg = Int8()
        msg.data = val
        self.led_pub.publish(msg)

    def send_buzzer_cmd(self, val: int):
        msg = Int8()
        msg.data = val
        self.buzzer_pub.publish(msg)

    def clear_active_timer(self):
        if self.active_timer:
            self.active_timer.cancel()
            self.active_timer = None

    def on_code_received(self, msg: String):
        code_id = msg.data.strip()
        self.get_logger().info(f"Vérification du code : {code_id}")

        user = get_user_by_code(code_id)
        is_granted, reason = check_access(user, target_zone="zone_interdite")

        status_str = "ok" if is_granted else "denied"
        now_ts = datetime.now().isoformat(timespec="seconds")

        # 1. Enregistrement en base de données
        event_id = log_event(
            kind="scan",
            code_id=code_id,
            status=status_str,
            persons=0,
            snapshot=None
        )

        # 2. Publication du résultat d'accès (JSON)
        payload = {
            "event_id": event_id,
            "ts": now_ts,
            "code_id": code_id,
            "status": status_str,
            "reason": reason,
            "user": user
        }
        res_msg = String()
        res_msg.data = json.dumps(payload)
        self.result_pub.publish(res_msg)

        # 3. Actions matérielles (LED & Buzzer)
        self.clear_active_timer()

        if is_granted:
            self.alarm_active = False
            self.get_logger().info(f"Accès ACCORDÉ pour {user['name'] if user else code_id}. LED verte allumée.")
            self.send_led_cmd(1)       # LED verte
            self.send_buzzer_cmd(2)    # Bip court de validation
            # Extinction automatique après 5 s
            self.active_timer = threading.Timer(self.valid_duration_s, self._turn_off_all)
            self.active_timer.start()
        else:
            self.alarm_active = True
            self.latest_denied_event_id = event_id
            self.get_logger().warning(f"Accès REFUSÉ ({reason}). LED rouge et alarme activées.")
            self.send_led_cmd(2)       # LED rouge
            self.send_buzzer_cmd(1)    # Alarme buzzer (bips répétés)
            # Timeout de sécurité maximum à 10 s
            self.active_timer = threading.Timer(self.alarm_max_s, self._turn_off_all)
            self.active_timer.start()

    def on_alarm_ack(self, msg: Empty):
        """Acquittement de l'alarme depuis l'interface web."""
        self.get_logger().info("Acquittement reçu (/system/ack). Extinction LED et buzzer.")
        self.clear_active_timer()
        self._turn_off_all()

    def on_intrusion_info(self, msg: String):
        """Met à jour l'événement avec les résultats de vision (nombre de personnes et snapshot)."""
        try:
            data = json.loads(msg.data)
            snapshot = data.get("snapshot")
            persons = data.get("persons", 0)
            if self.latest_denied_event_id:
                from sentinelai.db import get_connection
                with get_connection() as con:
                    con.execute(
                        "UPDATE events SET snapshot = ?, persons = ? WHERE id = ?",
                        (snapshot, persons, self.latest_denied_event_id)
                    )
                self.get_logger().info(f"Événement #{self.latest_denied_event_id} mis à jour avec {persons} personne(s) et snapshot {snapshot}")
        except Exception as e:
            self.get_logger().error(f"Erreur mise à jour intrusion_info : {e}")

    def _turn_off_all(self):
        self.alarm_active = False
        self.send_led_cmd(0)
        self.send_buzzer_cmd(0)

    def destroy_node(self):
        self.clear_active_timer()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = AccessNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
