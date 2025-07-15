from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=False)
    tags = Column(String, default="")
    snmp_community = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
