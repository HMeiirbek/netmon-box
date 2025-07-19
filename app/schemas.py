from pydantic import BaseModel, IPvAnyAddress
from typing import List, Optional
from datetime import datetime

class DeviceCreate(BaseModel):
    ip_address: IPvAnyAddress
    description: str
    tags: Optional[List[str]] = []
    snmp_community: Optional[str] = None

class DeviceUpdate(BaseModel):
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    snmp_community: Optional[str] = None
    is_active: Optional[bool] = None

class Device(DeviceCreate):
    id: int
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True

class PingResultBase(BaseModel):
    is_alive: bool
    response_time: Optional[float] = None
    packet_loss: float = 0.0
    error_message: Optional[str] = None

class PingResultCreate(PingResultBase):
    device_id: int

class PingResult(PingResultBase):
    id: int
    device_id: int
    timestamp: datetime
    
    class Config:
        from_attributes = True

class DeviceWithStatus(Device):
    last_ping: Optional[PingResult] = None
    availability_percentage: Optional[float] = None
