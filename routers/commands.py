from fastapi import APIRouter, HTTPException, status
from database import db
from models import CommandRequest, Command
from datetime import datetime
from bson import ObjectId
from mqtt_client import mqtt
import json

router = APIRouter()

# API gửi lệnh điều khiển endpoint qua MQTT
@router.post("/", status_code=status.HTTP_201_CREATED)
async def send_command(cmd_req: CommandRequest):
    if not cmd_req.deviceId:
        raise HTTPException(status_code=400, detail="Thiếu deviceId")
    
    # Validate endpoint ID
    if cmd_req.endpointId < 1 or cmd_req.endpointId > 3:
        raise HTTPException(status_code=400, detail="endpointId phải từ 1 đến 3 (chỉ điều khiển đèn)")

    device_id = cmd_req.deviceId
    
    # Validate ObjectId format
    try:
        device_obj_id = ObjectId(device_id)
    except Exception:
        raise HTTPException(status_code=400, detail=f"deviceId không hợp lệ: '{device_id}' (phải là 24 ký tự hex)")

    device = await db.devices.find_one({"_id": device_obj_id})
    if not device:
        raise HTTPException(status_code=404, detail="Thiết bị không tồn tại")

    new_command = Command(
        commandId=str(ObjectId()),
        deviceId=device_id,
        endpointId=cmd_req.endpointId,
        command=cmd_req.command,
        payload=cmd_req.payload,
        status="PENDING",
        createdAt=datetime.now()
    )

    await db.commands.insert_one(new_command.model_dump(by_alias=True, exclude=["id"]))

    room_id = device.get("roomId")
    if not room_id:
        raise HTTPException(status_code=400, detail="Thiết bị chưa được gán vào phòng")

    target_val = 1 if cmd_req.command == "TURN_ON" else 0

    # === ĐẢM BẢO DEVICE CÓ currentLampStates (khởi tạo nếu chưa có) ===
    if "currentLampStates" not in device or device.get("currentLampStates") is None:
        await db.devices.update_one(
            {"_id": device_obj_id},
            {"$set": {"currentLampStates": {"device1": 0, "device2": 0, "device3": 0}}}
        )

    # === CẬP NHẬT DATABASE: currentLampStates + endpoints ===
    update_data = {
        f"currentLampStates.device{cmd_req.endpointId}": target_val
    }
    
    # 1) Cập nhật currentLampStates luôn
    await db.devices.update_one(
        {"_id": device_obj_id},
        {"$set": update_data}
    )
    
    # 2) Cũng cập nhật endpoint nếu tồn tại
    result = await db.devices.update_one(
        {"_id": device_obj_id, "endpoints.id": cmd_req.endpointId},
        {"$set": {
            "endpoints.$.value": target_val,
            "endpoints.$.lastUpdated": datetime.now()
        }}
    )
    
    if result.matched_count == 0:
        print(f"[WARN] Endpoint {cmd_req.endpointId} không tìm thấy trong array endpoints")
    
    # === LẤY TRẠNG THÁI MỚI TỪ currentLampStates (ƯU TIÊN) ===
    updated_device = await db.devices.find_one({"_id": device_obj_id})
    lamp_states = updated_device.get("currentLampStates", {})

    payload = {
        "device1": lamp_states.get("device1", 0),
        "device2": lamp_states.get("device2", 0),
        "device3": lamp_states.get("device3", 0),
    }

    topic = f"{room_id}/device"
    payload_json = json.dumps(payload)
    
    # Kiểm tra MQTT connection
    if not mqtt.client or not mqtt.client.is_connected:
        print("[ERROR] MQTT client not connected!")
        raise HTTPException(status_code=503, detail="MQTT broker không kết nối")
    
    # Publish với QoS=1 để đảm bảo ESP nhận được
    mqtt.publish(topic, payload_json, qos=1)
    print(f"[COMMAND] Published to {topic}: {payload_json}")

    return {
        "message": "Đã gửi lệnh xuống thiết bị",
        "commandId": new_command.commandId,
        "mqtt_topic": topic,
        "payload": payload
    }

# API lấy lịch sử lệnh
@router.get("/history/{device_id}")
async def get_command_history(
    device_id: str,
    limit: int = 20,
    skip: int = 0
):
    device = await db.devices.find_one({"_id": ObjectId(device_id)})
    if not device:
        raise HTTPException(status_code=404, detail="Thiết bị không tồn tại")

    cursor = db.commands.find({"deviceId": device_id}).sort("createdAt", -1).skip(skip).limit(limit)
    
    history = await cursor.to_list(length=limit)

    result = []
    for cmd in history:
        ep_name = "Unknown"
        for ep in device.get("endpoints", []):
            if ep["id"] == cmd["endpointId"]:
                ep_name = ep["name"]
                break

        result.append({
            "commandId": cmd.get("commandId"),
            "endpointId": cmd["endpointId"],
            "endpointName": ep_name,
            "command": cmd["command"],
            "status": cmd["status"],
            "createdAt": cmd["createdAt"],
            "ackedAt": cmd.get("ackedAt")
        })

    return result
