from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from database import db
from routers import rooms, devices, commands
from mqtt_client import mqtt
from datetime import datetime
import json

# Quản lý vòng đời app
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khi server khởi động
    await mqtt.mqtt_startup()
    yield  # Server bắt đầu chạy
    
    # Khi server tắt
    await mqtt.mqtt_shutdown()
    print("Server đang tắt...")

app = FastAPI(lifespan=lifespan)

# ==================== CORS Configuration ====================
# Cho phép tất cả origins (dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép mọi domain
    allow_credentials=True,
    allow_methods=["*"],  # Cho phép GET, POST, PUT, DELETE...
    allow_headers=["*"],  # Cho phép tất cả headers
)
# ============================================================

mqtt.init_app(app)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Smart Home Backend API",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "rooms": "/rooms",
            "devices": "/devices",
            "health": "/health",
            "mqtt-status": "/mqtt-status"
        }
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

# MQTT status endpoint
@app.get("/mqtt-status")
async def mqtt_status():
    is_connected = mqtt.client is not None and mqtt.client.is_connected()
    return {
        "mqtt_connected": is_connected,
        "broker_host": "5b495904868d4c9e9e07c33dde4f6274.s1.eu.hivemq.cloud",
        "broker_port": 8883,
        "status": "Connected ✅" if is_connected else "Disconnected ❌"
    }

# Đăng ký các Router
app.include_router(rooms.router, prefix="/rooms", tags=["Rooms"])
app.include_router(devices.router, prefix="/devices", tags=["Devices"])
app.include_router(commands.router, prefix="/commands", tags=["Commands"])

# MQTT Event Handlers
@mqtt.on_connect()
def connect(client, flags, rc, properties):
    print(f"[MQTT] Connected to broker! rc={rc}, flags={flags}")
    mqtt.client.subscribe("+/+")
    print("[MQTT] Subscribed to +/+ (all topics)")

@mqtt.on_message()
async def message(client, topic, payload, qos, properties):
    try:
        payload_str = payload.decode()
        print(f"[MQTT IN] Received: {topic} -> {payload_str} (qos={qos})")

        parts = topic.split("/")
        if len(parts) == 2:
            room_id = parts[0]
            type_msg = parts[1]

            try:
                data = json.loads(payload_str)
            except json.JSONDecodeError:
                data = payload_str

            # Xử lý theo loại message
            if type_msg == "device":
                print(f"[MQTT IN] Processing device update for room {room_id}: {data}")
                if isinstance(data, dict):
                    # Cập nhật currentLampStates trước
                    update_lamp_states = {}
                    for key, val in data.items():
                        if key.startswith("device") and key in ["device1", "device2", "device3"]:
                            update_lamp_states[f"currentLampStates.{key}"] = val

                    if update_lamp_states:
                        await db.devices.update_one(
                            {"roomId": room_id},
                            {
                                "$set": {
                                    **update_lamp_states,
                                    "isOnline": True,
                                    "lastSeenAt": datetime.now()
                                }
                            }
                        )

                    # Cập nhật từng endpoint
                    for key, val in data.items():
                        try:
                            if key.startswith("device"):
                                endpoint_id = int(key.replace("device", ""))

                                result = await db.devices.update_one(
                                    {"roomId": room_id, "endpoints.id": endpoint_id},
                                    {
                                        "$set": {
                                            "endpoints.$.value": val,
                                            "endpoints.$.lastUpdated": datetime.now(),
                                        }
                                    }
                                )
                                if result.matched_count > 0:
                                    print(f"-> Update: Phòng {room_id} - Ep {endpoint_id} = {val}")
                        except ValueError:
                            continue
                else:
                    print("Lỗi: Payload device phải là JSON Object")

            elif type_msg == "status":
                SENSOR_ENDPOINT_ID = 4

                # Cập nhật currentSensorData
                if isinstance(data, dict):
                    await db.devices.update_one(
                        {"roomId": room_id},
                        {
                            "$set": {
                                "currentSensorData.temperature": data.get("temperature", 0.0),
                                "currentSensorData.humidity": data.get("humidity", 0.0),
                                "isOnline": True
                            }
                        }
                    )

                result = await db.devices.update_one(
                    {"roomId": room_id, "endpoints.id": SENSOR_ENDPOINT_ID},
                    {
                        "$set": {
                            "endpoints.$.value": data,
                            "endpoints.$.lastUpdated": datetime.now(),
                        }
                    }
                )

                if result.matched_count > 0:
                    print(f"-> Update Sensor phòng {room_id}: {data}")
                else:
                    print(f"Cảnh báo: Không tìm thấy Sensor (id=4) ở phòng {room_id}")

    except Exception as e:
        print(f"Lỗi xử lý MQTT: {e}")
