"""Web bridge node for SentinelAI (FastAPI + WebSocket + ROS 2).

Sert :
- L'interface web statique (web/)
- L'API REST (/api/events, /api/users, /api/stats, /api/ack, /snapshots)
- Le flux vidéo live MJPEG (/api/camera/stream)
- Le WebSocket (/ws) en temps réel avec notification instantanée des événements
"""

import asyncio
import json
import os
import secrets
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Empty, Int8

from sentinelai.db import get_recent_events, get_all_users, get_connection
from sentinelai.vision_node import VisionNode

# Dossiers statiques et snapshots
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
WEB_DIR = BASE_DIR / "web"
SNAPSHOT_DIR = BASE_DIR / "data" / "snapshots"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="SentinelAI Web Bridge", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gestionnaire de connexions WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.loop = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_json(self, data: dict):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(dead)

    def threadsafe_broadcast(self, data: dict):
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast_json(data), self.loop)

manager = ConnectionManager()

# Sessions valides temporaires
valid_sessions = {}  # token -> expiration timestamp

class WebBridgeROS(Node):
    def __init__(self):
        super().__init__('web_bridge_node')

        # Abonnements
        self.access_sub = self.create_subscription(String, '/access/result', self.on_access_result, 10)
        self.intrusion_sub = self.create_subscription(String, '/intrusion/info', self.on_intrusion_info, 10)
        self.esp32_sub = self.create_subscription(String, '/esp32/status', self.on_esp32_status, 10)

        # Publications
        self.ack_pub = self.create_publisher(Empty, '/system/ack', 10)
        self.scan_sim_pub = self.create_publisher(String, '/scan/code', 10)

        self.get_logger().info('WebBridgeROS connecté à ROS 2.')

    def on_access_result(self, msg: String):
        try:
            data = json.loads(msg.data)
            # Générer un jeton de session en cas d'accès valide
            if data.get("status") == "ok":
                token = secrets.token_hex(16)
                valid_sessions[token] = time.time() + 300 # 5 minutes
                data["session_token"] = token

            manager.threadsafe_broadcast({
                "type": "access_result",
                "data": data
            })
        except Exception as e:
            self.get_logger().error(f"Erreur access_result WS : {e}")

    def on_intrusion_info(self, msg: String):
        try:
            data = json.loads(msg.data)
            manager.threadsafe_broadcast({
                "type": "intrusion_info",
                "data": data
            })
        except Exception as e:
            self.get_logger().error(f"Erreur intrusion_info WS : {e}")

    def on_esp32_status(self, msg: String):
        try:
            data = json.loads(msg.data)
            manager.threadsafe_broadcast({
                "type": "esp32_status",
                "data": data
            })
        except Exception as e:
            pass

    def publish_ack(self):
        self.ack_pub.publish(Empty())

    def simulate_scan(self, code: str):
        msg = String()
        msg.data = code
        self.scan_sim_pub.publish(msg)

ros_bridge_node: WebBridgeROS = None

# --- Routes API REST ---

@app.get("/api/events")
async def api_events(limit: int = 50):
    return get_recent_events(limit=limit)

@app.get("/api/users")
async def api_users():
    return get_all_users()

@app.post("/api/users")
async def api_create_or_update_user(user: dict):
    code_id = user.get("code_id")
    name = user.get("name")
    grp = user.get("grp", "Visiteur")
    level = int(user.get("level", 1))
    zone = user.get("zone", "zone_libre")
    active = int(user.get("active", 1))

    if not code_id or not name:
        raise HTTPException(status_code=400, detail="code_id et name sont obligatoires")

    with get_connection() as con:
        con.execute("""
            INSERT INTO users (code_id, name, grp, level, zone, active)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(code_id) DO UPDATE SET
                name=excluded.name,
                grp=excluded.grp,
                level=excluded.level,
                zone=excluded.zone,
                active=excluded.active
        """, (code_id, name, grp, level, zone, active))

    return {"status": "ok", "user": user}

@app.get("/api/stats")
async def api_stats():
    with get_connection() as con:
        cur = con.cursor()
        cur.execute("SELECT status, COUNT(*) FROM events GROUP BY status")
        counts = dict(cur.fetchall())
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]

    return {
        "total_granted": counts.get("ok", 0),
        "total_denied": counts.get("denied", 0),
        "total_users": total_users,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/ack")
async def api_ack():
    if ros_bridge_node:
        ros_bridge_node.publish_ack()
        return {"status": "ack_sent"}
    raise HTTPException(status_code=503, detail="ROS 2 non disponible")

@app.post("/api/scan")
async def api_scan(request: Request):
    """Permet de simuler ou déclencher un scan depuis l'interface web (laptop/mobile)."""
    body = await request.json()
    code = body.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Code manquant")
    if ros_bridge_node:
        ros_bridge_node.simulate_scan(code)
        return {"status": "scanned", "code": code}
    raise HTTPException(status_code=503, detail="ROS 2 non disponible")

@app.get("/snapshots/{filename}")
async def get_snapshot(filename: str):
    file_path = SNAPSHOT_DIR / filename
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Capture introuvable")
    return FileResponse(file_path, media_type="image/jpeg")

def gen_mjpeg_stream():
    """Générateur du flux vidéo MJPEG à partir de VisionNode."""
    while True:
        with VisionNode.latest_jpeg_lock:
            frame = VisionNode.latest_jpeg
        if frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.04)

@app.get("/api/camera/stream")
async def camera_stream():
    return StreamingResponse(
        gen_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    # Envoyer un premier état de bienvenue
    await websocket.send_json({
        "type": "connected",
        "timestamp": datetime.now().isoformat()
    })
    try:
        while True:
            data = await websocket.receive_text()
            # Commandes potentielles envoyées par le client web
            try:
                cmd = json.loads(data)
                if cmd.get("action") == "ack" and ros_bridge_node:
                    ros_bridge_node.publish_ack()
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Servir les fichiers web statiques
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="static")

def main(args=None):
    global ros_bridge_node
    rclpy.init(args=args)
    ros_bridge_node = WebBridgeROS()

    # Démarrage du thread ROS 2
    ros_thread = threading.Thread(target=rclpy.spin, args=(ros_bridge_node,), daemon=True)
    ros_thread.start()

    # Capture de la boucle événementielle asyncio pour le websocket broadcast
    host = os.environ.get("WEB_HOST", "0.0.0.0")
    port = int(os.environ.get("WEB_PORT", 8000))

    config = uvicorn.Config(app=app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)

    # Récupérer l'event loop dans le thread principal
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    manager.loop = loop

    try:
        loop.run_until_complete(server.serve())
    except KeyboardInterrupt:
        pass
    finally:
        ros_bridge_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
