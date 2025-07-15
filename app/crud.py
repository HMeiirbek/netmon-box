from . import models, schemas
from sqlalchemy.orm import Session

def create_device(db: Session, device: schemas.DeviceCreate):
    db_device = models.Device(
        ip_address=str(device.ip_address),
        description=device.description,
        tags=",".join(device.tags),
        snmp_community=device.snmp_community,
    )
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device
