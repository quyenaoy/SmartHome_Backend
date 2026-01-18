from pydantic import BaseModel, Field, BeforeValidator
from typing import Optional, Union, List
from datetime import datetime
from typing_extensions import Annotated

# Chuyển ObjectId của MongoDB thành String
PyObjectId = Annotated[str, BeforeValidator(str)]

# Model cơ sở
class MongoBaseModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda dt: dt.isoformat()}

# Room - Phòng
class Room(MongoBaseModel):
    name: str
    floor: Optional[int] = None
    createdAt: datetime = Field(default_factory=datetime.now)

# DeviceEndpoint - Điểm điều khiển
class DeviceEndpoint(BaseModel):
    id: int
    name: str
    type: str # SWITCH hoặc SENSOR
    value: Union[int, dict] = None
    lastUpdated: datetime = Field(default_factory=datetime.now)

# Device - Thiết bị ESP
class Device(MongoBaseModel):
    roomId: str # Liên kết tới phòng
    endpoints: List[DeviceEndpoint] = []
    name: str
    serialNo: Optional[str] = None
    bleMac: Optional[str] = None
    ipAddress: Optional[str] = None
    isOnline: bool = False
    lastSeenAt: Optional[datetime] = None
    createdAt: datetime = Field(default_factory=datetime.now)
    
    # Thêm fields lưu trạng thái trực tiếp
    currentLampStates: Optional[dict] = Field(default_factory=lambda: {"device1": 0, "device2": 0, "device3": 0})
    currentSensorData: Optional[dict] = Field(default_factory=lambda: {"temperature": 0.0, "humidity": 0.0})

# Command - Lệnh điều khiển
class Command(MongoBaseModel):
    commandId: str
    deviceId: str
    endpointId: int
    command: str # TURN_ON, TURN_OFF, SET_VALUE
    payload: Optional[str] = None
    status: str = "PENDING" # PENDING, SENT, ACKED, FAILED
    createdAt: datetime = Field(default_factory=datetime.now)
    ackedAt: Optional[datetime] = None

# ===== Request Models =====

class RoomCreateRequest(BaseModel):
    name: str
    floor: Optional[int] = None

class RoomUpdateRequest(BaseModel):
    name: Optional[str] = None
    floor: Optional[int] = None

class DeviceCreateRequest(BaseModel):
    roomId: str
    name: str

class DeviceUpdateRequest(BaseModel):
    name: Optional[str] = None
    roomId: Optional[str] = None

class EndpointCreateRequest(BaseModel):
    id: int
    name: str
    type: str = "SWITCH"

class EndpointUpdateRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None

class CommandRequest(BaseModel):
    deviceId: Optional[str] = None
    endpointId: int
    command: str # TURN_ON, TURN_OFF
    payload: Optional[str] = None