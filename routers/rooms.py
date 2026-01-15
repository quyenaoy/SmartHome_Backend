from fastapi import APIRouter, HTTPException, status
from typing import List
from database import db
from models import Room, RoomCreateRequest, RoomUpdateRequest
from datetime import datetime
from bson import ObjectId

router = APIRouter()

# API tạo phòng mới
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_room(room_req: RoomCreateRequest):
    new_room = Room(
        name=room_req.name,
        floor=room_req.floor,
        createdAt=datetime.now()
    )

    result = await db.rooms.insert_one(new_room.model_dump(by_alias=True, exclude=["id"]))

    return {
        "message": "Tạo phòng thành công", 
        "roomId": str(result.inserted_id)
    }

# API lấy danh sách tất cả phòng
@router.get("/", response_model=List[Room])
async def get_all_rooms():
    rooms_cursor = db.rooms.find({})
    rooms = await rooms_cursor.to_list(length=100)
    return rooms

# API lấy chi tiết phòng
@router.get("/{room_id}", response_model=Room)
async def get_room(room_id: str):
    room = await db.rooms.find_one({"_id": ObjectId(room_id)})
    if not room:
        raise HTTPException(status_code=404, detail="Phòng không tồn tại")
    return room

# API cập nhật phòng
@router.put("/{room_id}")
async def update_room(
    room_id: str,
    room_req: RoomUpdateRequest
):
    room = await db.rooms.find_one({"_id": ObjectId(room_id)})
    if not room:
        raise HTTPException(status_code=404, detail="Phòng không tồn tại")

    update_data = {}
    if room_req.name:
        update_data["name"] = room_req.name
    if room_req.floor is not None:
        update_data["floor"] = room_req.floor

    if not update_data:
        return {"message": "Không có thông tin nào thay đổi"}

    await db.rooms.update_one(
        {"_id": ObjectId(room_id)},
        {"$set": update_data}
    )

    return {"message": "Cập nhật phòng thành công"}

# API xóa phòng
@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(room_id: str):
    room = await db.rooms.find_one({"_id": ObjectId(room_id)})
    if not room:
        raise HTTPException(status_code=404, detail="Phòng không tồn tại")

    # Xóa tất cả device trong phòng
    await db.devices.delete_many({"roomId": room_id})
    
    # Xóa phòng
    await db.rooms.delete_one({"_id": ObjectId(room_id)})

    return None