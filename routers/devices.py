from fastapi import APIRouter, HTTPException, status
from typing import List
from database import db
from models import CommandRequest, Device, DeviceCreateRequest, DeviceUpdateRequest, Command, EndpointCreateRequest, EndpointUpdateRequest, DeviceEndpoint
from datetime import datetime
from bson import ObjectId
from mqtt_client import mqtt
import json

router = APIRouter()

# API tạo thiết bị (ESP) mới cho phòng
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_device(device_req: DeviceCreateRequest):
    # Kiểm tra phòng tồn tại
    room = await db.rooms.find_one({"_id": ObjectId(device_req.roomId)})
    if not room:
        raise HTTPException(status_code=404, detail="Phòng không tồn tại")

    new_device = Device(
        roomId=device_req.roomId,
        name=device_req.name,
        endpoints=[],
        createdAt=datetime.now()
    )

    result = await db.devices.insert_one(new_device.model_dump(by_alias=True, exclude=["id"]))

    return {
        "message": "Tạo thiết bị thành công",
        "deviceId": str(result.inserted_id)
    }

# API cập nhật device
@router.put("/{device_id}")
async def update_device(
    device_id: str,
    req: DeviceUpdateRequest
):
    device = await db.devices.find_one({"_id": ObjectId(device_id)})
    if not device:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")

    update_data = {}

    if req.name:
        update_data["name"] = req.name

    # Cập nhật phòng
    if req.roomId:
        if req.roomId != device.get("roomId"):
            target_room = await db.rooms.find_one({"_id": ObjectId(req.roomId)})
            if not target_room:
                raise HTTPException(status_code=404, detail="Phòng mới không tồn tại")
            update_data["roomId"] = req.roomId

    if not update_data:
        return {"message": "Không có thông tin nào thay đổi"}

    await db.devices.update_one(
        {"_id": ObjectId(device_id)},
        {"$set": update_data}
    )

    return {"message": "Cập nhật thiết bị thành công"}

# API xóa thiết bị
@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(device_id: str):
    device = await db.devices.find_one({"_id": ObjectId(device_id)})
    if not device:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")

    # Xóa commands liên quan
    await db.commands.delete_many({"deviceId": device_id})
    
    # Xóa thiết bị
    await db.devices.delete_one({"_id": ObjectId(device_id)})

    return None

# API thêm endpoint mới cho device
@router.post("/{device_id}/endpoints", status_code=status.HTTP_201_CREATED)
async def add_endpoint(
    device_id: str,
    endpoint_req: EndpointCreateRequest
):
    device = await db.devices.find_one({"_id": ObjectId(device_id)})
    if not device:
        raise HTTPException(status_code=404, detail="Thiết bị không tồn tại")

    for ep in device.get("endpoints", []):
        if ep["id"] == endpoint_req.id:
            raise HTTPException(status_code=400, detail="ID endpoint đã tồn tại")

    new_endpoint = DeviceEndpoint(
        id=endpoint_req.id,
        name=endpoint_req.name,
        type=endpoint_req.type,
        value=0,
        lastUpdated=datetime.now()
    )

    await db.devices.update_one(
        {"_id": ObjectId(device_id)},
        {"$push": {"endpoints": new_endpoint.model_dump()}}
    )

    return {"message": "Đã thêm endpoint mới"}

# API cập nhật endpoint
@router.put("/{device_id}/endpoints/{endpoint_id}")
async def update_endpoint(
    device_id: str,
    endpoint_id: int,
    req: EndpointUpdateRequest
):
    device = await db.devices.find_one({"_id": ObjectId(device_id)})
    if not device:
        raise HTTPException(status_code=404, detail="Thiết bị không tồn tại")

    update_fields = {}
    if req.name: 
        update_fields["endpoints.$.name"] = req.name
    if req.type: 
        update_fields["endpoints.$.type"] = req.type

    if not update_fields:
        return {"message": "Không có dữ liệu thay đổi"}

    result = await db.devices.update_one(
        {"_id": ObjectId(device_id), "endpoints.id": endpoint_id},
        {"$set": update_fields}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Endpoint không tìm thấy")

    return {"message": "Cập nhật thành công"}

# API xóa endpoint
@router.delete("/{device_id}/endpoints/{endpoint_id}")
async def delete_endpoint(
    device_id: str,
    endpoint_id: int
):
    device = await db.devices.find_one({"_id": ObjectId(device_id)})
    if not device:
        raise HTTPException(status_code=404, detail="Thiết bị không tồn tại")

    # Xóa commands liên quan tới endpoint này
    await db.commands.delete_many({"deviceId": device_id, "endpointId": endpoint_id})
    
    # Xóa endpoint khỏi device
    await db.devices.update_one(
        {"_id": ObjectId(device_id)},
        {"$pull": {"endpoints": {"id": endpoint_id}}}
    )

    return {"message": "Đã xóa endpoint"}

# API lấy danh sách thiết bị theo phòng
@router.get("/room/{room_id}", response_model=List[Device])
async def get_devices_by_room(room_id: str):
    room = await db.rooms.find_one({"_id": ObjectId(room_id)})
    if not room:
        raise HTTPException(status_code=404, detail="Phòng không tồn tại")

    devices = await db.devices.find({"roomId": room_id}).to_list(length=100)
    return devices

# API lấy chi tiết device
@router.get("/{device_id}", response_model=Device)
async def get_device(device_id: str):
    device = await db.devices.find_one({"_id": ObjectId(device_id)})
    if not device:
        raise HTTPException(status_code=404, detail="Thiết bị không tồn tại")
    return device

# API gửi lệnh điều khiển endpoint qua MQTT
@router.post("/{device_id}/command", status_code=status.HTTP_201_CREATED)
async def send_command(
    device_id: str,
    cmd_req: CommandRequest
):
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

    # Gửi lệnh qua MQTT
    room_id = device.get("roomId")
    if not room_id:
        raise HTTPException(status_code=400, detail="Thiết bị chưa được gán vào phòng")

    payload = {}

    target_val = 0
    if cmd_req.command == "TURN_ON":
        target_val = 1
    elif cmd_req.command == "TURN_OFF":
        target_val = 0

    # Tạo payload đầy đủ cho tất cả các endpoint (device1, device2, device3)
    for i in range(1, 4):
        key = f"device{i}"

        if i == cmd_req.endpointId:
            payload[key] = target_val
        else:
            current_val = 0
            for ep in device.get("endpoints", []):
                if ep["id"] == i:
                    if ep.get("value") == 1: 
                        current_val = 1
                    break
            payload[key] = current_val

    topic = f"{room_id}/device"
    mqtt.publish(topic, json.dumps(payload))

    return {
        "message": "Đã gửi lệnh xuống thiết bị", 
        "mqtt_topic": topic, 
        "payload": payload
    }

# API lấy lịch sử lệnh của device
@router.get("/{device_id}/history")
async def get_device_history(
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