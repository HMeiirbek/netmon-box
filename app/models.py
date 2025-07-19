from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
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
    is_active = Column(Boolean, default=True)
    
    # Relationship to ping results
    ping_results = relationship("PingResult", back_populates="device")

class PingResult(Base):
    __tablename__ = "ping_results"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_alive = Column(Boolean, nullable=False)
    response_time = Column(Float, nullable=True)  # in milliseconds
    packet_loss = Column(Float, default=0.0)  # percentage
    error_message = Column(String, nullable=True)
    
    # Relationship to device
    device = relationship("Device", back_populates="ping_results")
