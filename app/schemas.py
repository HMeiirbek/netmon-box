from pydantic import BaseModel, IPvAnyAddress
from typing import List, Optional

class DeviceCreate(BaseModel):
    ip_address: IPvAnyAddress
    description: str
    tags: Optional[List[str]] = []
    snmp_community: Optional[str] = None
