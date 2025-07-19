from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import asyncio
import logging

from app import models, schemas, crud, database, metrics
from app.monitor_service import monitor_service

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создание таблиц базы данных при запуске
models.Base.metadata.create_all(bind=database.engine)

# Создание FastAPI приложения с метаданными
app = FastAPI(
    title="NetMon Box",
    description="Network monitoring service for laboratory networks",
    version="1.0.0"
)

def get_db():
    """Dependency для получения сессии базы данных"""
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
async def startup_event():
    """Событие запуска приложения - запускаем мониторинг"""
    logger.info("Starting NetMon Box application")
    # Запускаем мониторинг в фоновом режиме каждые 60 секунд
    asyncio.create_task(monitor_service.start_monitoring(interval_seconds=60))

@app.on_event("shutdown")
async def shutdown_event():
    """Событие остановки приложения - останавливаем мониторинг"""
    logger.info("Shutting down NetMon Box application")
    await monitor_service.stop_monitoring()

@app.get("/", response_class=HTMLResponse)
def read_root():
    """Главная страница с HTML интерфейсом и описанием API"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>NetMon Box</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
            .section { margin: 20px 0; }
            .endpoint { background: #f9f9f9; padding: 10px; margin: 5px 0; border-left: 3px solid #007cba; }
            .endpoint h4 { margin: 0 0 5px 0; }
            .endpoint p { margin: 0; color: #666; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🌐 NetMon Box</h1>
                <p>Network monitoring service for laboratory networks</p>
            </div>
            
            <div class="section">
                <h2>📊 API Endpoints</h2>
                
                <div class="endpoint">
                    <h4>GET /devices</h4>
                    <p>List all active devices with their status</p>
                </div>
                
                <div class="endpoint">
                    <h4>POST /devices</h4>
                    <p>Register a new network device</p>
                </div>
                
                <div class="endpoint">
                    <h4>GET /devices/{device_id}</h4>
                    <p>Get device details and ping history</p>
                </div>
                
                <div class="endpoint">
                    <h4>PUT /devices/{device_id}</h4>
                    <p>Update device information</p>
                </div>
                
                <div class="endpoint">
                    <h4>DELETE /devices/{device_id}</h4>
                    <p>Deactivate a device (soft delete)</p>
                </div>
                
                <div class="endpoint">
                    <h4>POST /devices/{device_id}/ping</h4>
                    <p>Manually ping a device</p>
                </div>
                
                <div class="endpoint">
                    <h4>GET /metrics</h4>
                    <p>Prometheus metrics endpoint</p>
                </div>
                
                <div class="endpoint">
                    <h4>GET /docs</h4>
                    <p>Interactive API documentation (Swagger UI)</p>
                </div>
            </div>
            
            <div class="section">
                <h2>🔗 Quick Links</h2>
                <p><a href="/docs">📖 API Documentation</a></p>
                <p><a href="/metrics">📊 Prometheus Metrics</a></p>
                <p><a href="/devices">📱 Device List</a></p>
            </div>
        </div>
    </body>
    </html>
    """

# ============================================================================
# ENDPOINTS ДЛЯ УПРАВЛЕНИЯ УСТРОЙСТВАМИ
# ============================================================================

@app.post("/devices", response_model=dict)
def register_device(device: schemas.DeviceCreate, db: Session = Depends(get_db)):
    """Регистрация нового сетевого устройства для мониторинга"""
    # Проверяем, не существует ли уже устройство с таким IP
    existing_device = crud.get_device_by_ip(db, str(device.ip_address))
    if existing_device:
        raise HTTPException(status_code=400, detail="Device with this IP address already exists")
    
    # Создаем устройство и возвращаем его данные
    created_device = crud.create_device(db, device)
    return crud._convert_device_to_dict(created_device)

@app.get("/devices", response_model=List[dict])
def list_devices(
    skip: int = 0, 
    limit: int = 100, 
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Получение списка всех устройств с их текущим статусом"""
    if active_only:
        # Возвращаем только активные устройства со статусом
        return crud.get_devices_with_status(db, skip=skip, limit=limit)
    else:
        # Возвращаем все устройства (включая неактивные)
        devices = crud.get_devices(db, skip=skip, limit=limit, active_only=False)
        return [crud._convert_device_to_dict(device) for device in devices]

@app.get("/devices/{device_id}", response_model=dict)
def get_device(device_id: int, db: Session = Depends(get_db)):
    """Получение детальной информации об устройстве и истории ping"""
    device = crud.get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Получаем историю ping, последний результат и процент доступности
    ping_results = crud.get_device_ping_results(db, device_id, limit=50)
    last_ping = crud.get_last_ping_result(db, device_id)
    availability = crud.get_device_availability(db, device_id)
    
    return {
        "id": device.id,
        "ip_address": device.ip_address,
        "description": device.description,
        "tags": device.tags.split(",") if device.tags else [],
        "snmp_community": device.snmp_community,
        "created_at": device.created_at,
        "is_active": device.is_active,
        "last_ping": crud._convert_ping_result_to_dict(last_ping),
        "availability_percentage": availability,
        "ping_history": [crud._convert_ping_result_to_dict(pr) for pr in ping_results]
    }

@app.put("/devices/{device_id}", response_model=dict)
def update_device(
    device_id: int, 
    device_update: schemas.DeviceUpdate, 
    db: Session = Depends(get_db)
):
    """Обновление информации об устройстве"""
    updated_device = crud.update_device(db, device_id, device_update)
    if not updated_device:
        raise HTTPException(status_code=404, detail="Device not found")
    return crud._convert_device_to_dict(updated_device)

@app.delete("/devices/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    """Деактивация устройства (мягкое удаление)"""
    success = crud.delete_device(db, device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"message": "Device deactivated successfully"}

# ============================================================================
# ENDPOINTS ДЛЯ МОНИТОРИНГА
# ============================================================================

@app.post("/devices/{device_id}/ping")
async def ping_device(device_id: int):
    """Принудительный ping конкретного устройства"""
    result = await monitor_service.ping_device_manual(device_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@app.get("/devices/{device_id}/ping-history")
def get_device_ping_history(
    device_id: int, 
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Получение истории ping для конкретного устройства"""
    device = crud.get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    ping_results = crud.get_device_ping_results(db, device_id, limit=limit)
    return {
        "device_id": device_id,
        "device_ip": device.ip_address,
        "device_description": device.description,
        "ping_history": ping_results
    }

# ============================================================================
# СИСТЕМНЫЕ ENDPOINTS
# ============================================================================

@app.get("/metrics")
def get_metrics():
    """Endpoint для Prometheus метрик"""
    return StreamingResponse(
        iter([metrics.metrics_exporter.get_metrics()]),
        media_type="text/plain",
        headers=metrics.metrics_exporter.get_metrics_headers()
    )

@app.get("/health")
def health_check():
    """Проверка состояния системы"""
    return {
        "status": "healthy",
        "monitoring_active": monitor_service.is_running,
        "service": "NetMon Box"
    }