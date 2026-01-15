from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
from database import db
from routers import rooms, devices
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

mqtt.init_app(app)

# Đăng ký các Router
app.include_router(rooms.router, prefix="/rooms", tags=["Rooms"])
app.include_router(devices.router, prefix="/devices", tags=["Devices"])

# MQTT Event Handlers
@mqtt.on_connect()
def connect(client, flags, rc, properties):
    print("Đã kết nối tới MQTT Broker!")
    mqtt.client.subscribe("+/+")

@mqtt.on_message()
async def message(client, topic, payload, qos, properties):
    try:
        payload_str = payload.decode()
        print(f"Received message: {topic} -> {payload_str}")

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
                if isinstance(data, dict):
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
                                            "isOnline": True,
                                            "lastSeenAt": datetime.now()
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

                result = await db.devices.update_one(
                    {"roomId": room_id, "endpoints.id": SENSOR_ENDPOINT_ID},
                    {
                        "$set": {
                            "endpoints.$.value": data,
                            "endpoints.$.lastUpdated": datetime.now(),
                            "isOnline": True
                        }
                    }
                )

                if result.matched_count > 0:
                    print(f"-> Update Sensor phòng {room_id}: {data}")
                else:
                    print(f"Cảnh báo: Không tìm thấy Sensor (id=4) ở phòng {room_id}")

    except Exception as e:
        print(f"Lỗi xử lý MQTT: {e}")
