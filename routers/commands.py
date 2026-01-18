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

    device_id = cmd_req.deviceId

    device = await db.devices.find_one({"_id": ObjectId(device_id)})
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

    payload = {}
    for i in range(1, 4):
        key = f"device{i}"
        if i == cmd_req.endpointId:
            payload[key] = target_val
        else:
            current_val = 0
            for ep in device.get("endpoints", []):
                if ep["id"] == i and ep.get("value") == 1:
                    current_val = 1
                    break
            payload[key] = current_val

    topic = f"{room_id}/device"
    mqtt.publish(topic, json.dumps(payload))

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
