import asyncio
import logging
from typing import List
from sqlalchemy.orm import Session
from . import crud, models, schemas, ping_service, metrics
from .database import SessionLocal

logger = logging.getLogger(__name__)

class MonitorService:
    """Сервис для периодического мониторинга сетевых устройств"""
    
    def __init__(self, ping_service: ping_service.PingService):
        """
        Инициализация сервиса мониторинга
        
        Args:
            ping_service: Экземпляр сервиса для выполнения ping операций
        """
        self.ping_service = ping_service
        self.is_running = False
        self.monitoring_task = None
    
    async def start_monitoring(self, interval_seconds: int = 60):
        """
        Запуск периодического мониторинга всех активных устройств
        
        Args:
            interval_seconds: Интервал между проверками в секундах
        """
        if self.is_running:
            logger.warning("Monitoring is already running")
            return
        
        self.is_running = True
        logger.info(f"Starting device monitoring with {interval_seconds}s interval")
        
        # Основной цикл мониторинга
        while self.is_running:
            try:
                await self._monitor_all_devices()
                await asyncio.sleep(interval_seconds)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(5)  # Короткая задержка перед повторной попыткой
    
    async def stop_monitoring(self):
        """Остановка периодического мониторинга"""
        self.is_running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
        logger.info("Device monitoring stopped")
    
    async def _monitor_all_devices(self):
        """Мониторинг всех активных устройств"""
        db = SessionLocal()
        try:
            # Получаем список всех активных устройств
            devices = crud.get_devices(db, active_only=True)
            logger.debug(f"Monitoring {len(devices)} active devices")
            
            # Проверяем каждое устройство
            for device in devices:
                await self._monitor_device(device, db)
                
        except Exception as e:
            logger.error(f"Error monitoring devices: {str(e)}")
        finally:
            db.close()
    
    async def _monitor_device(self, device: models.Device, db: Session):
        """
        Мониторинг одного устройства
        
        Args:
            device: Модель устройства для мониторинга
            db: Сессия базы данных
        """
        try:
            # Выполняем ping
            ping_result = await self.ping_service.ping_device(device.ip_address)
            
            # Сохраняем результат в базу данных
            ping_data = schemas.PingResultCreate(
                device_id=device.id,
                is_alive=ping_result["is_alive"],
                response_time=ping_result["response_time"],
                packet_loss=ping_result["packet_loss"],
                error_message=ping_result["error_message"]
            )
            
            crud.create_ping_result(db, ping_data)
            
            # Обновляем метрики Prometheus
            metrics.metrics_exporter.record_ping_result(
                device_ip=device.ip_address,
                device_description=device.description,
                is_alive=ping_result["is_alive"],
                response_time=ping_result["response_time"],
                packet_loss=ping_result["packet_loss"]
            )
            
            # Логируем результат
            status = "UP" if ping_result["is_alive"] else "DOWN"
            response_time_str = f"{ping_result['response_time']:.2f}ms" if ping_result["response_time"] else "N/A"
            logger.info(f"Device {device.ip_address} ({device.description}): {status}, RTT: {response_time_str}")
            
        except Exception as e:
            logger.error(f"Error monitoring device {device.ip_address}: {str(e)}")
    
    async def ping_device_manual(self, device_id: int) -> dict:
        """
        Принудительный ping конкретного устройства
        
        Args:
            device_id: ID устройства для проверки
            
        Returns:
            Dict с результатами ping или ошибкой
        """
        db = SessionLocal()
        try:
            # Получаем устройство из базы
            device = crud.get_device(db, device_id)
            if not device:
                return {"error": "Device not found"}
            
            if not device.is_active:
                return {"error": "Device is inactive"}
            
            # Выполняем ping
            ping_result = await self.ping_service.ping_device(device.ip_address)
            
            # Сохраняем результат в базу данных
            ping_data = schemas.PingResultCreate(
                device_id=device.id,
                is_alive=ping_result["is_alive"],
                response_time=ping_result["response_time"],
                packet_loss=ping_result["packet_loss"],
                error_message=ping_result["error_message"]
            )
            
            saved_result = crud.create_ping_result(db, ping_data)
            
            # Обновляем метрики Prometheus
            metrics.metrics_exporter.record_ping_result(
                device_ip=device.ip_address,
                device_description=device.description,
                is_alive=ping_result["is_alive"],
                response_time=ping_result["response_time"],
                packet_loss=ping_result["packet_loss"]
            )
            
            # Возвращаем результат
            return {
                "device_id": device.id,
                "ip_address": device.ip_address,
                "description": device.description,
                "ping_result": {
                    "is_alive": ping_result["is_alive"],
                    "response_time": ping_result["response_time"],
                    "packet_loss": ping_result["packet_loss"],
                    "error_message": ping_result["error_message"],
                    "timestamp": saved_result.timestamp
                }
            }
            
        except Exception as e:
            logger.error(f"Error in manual ping for device {device_id}: {str(e)}")
            return {"error": str(e)}
        finally:
            db.close()

# Глобальный экземпляр сервиса мониторинга
ping_service_instance = ping_service.PingService()
monitor_service = MonitorService(ping_service_instance) 