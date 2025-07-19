from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from typing import Dict, List
import time

# ============================================================================
# PROMETHEUS МЕТРИКИ
# ============================================================================

# Счетчик общего количества ping запросов
ping_requests_total = Counter(
    'netmon_ping_requests_total',
    'Total number of ping requests',
    ['device_ip', 'status']
)

# Гистограмма времени отклика ping
ping_response_time = Histogram(
    'netmon_ping_response_time_seconds',
    'Ping response time in seconds',
    ['device_ip'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Gauge доступности устройства (1 = доступно, 0 = недоступно)
device_availability = Gauge(
    'netmon_device_availability',
    'Device availability (1 = available, 0 = unavailable)',
    ['device_ip', 'device_description']
)

# Gauge процента потери пакетов
packet_loss_percentage = Gauge(
    'netmon_packet_loss_percentage',
    'Packet loss percentage',
    ['device_ip']
)

class MetricsExporter:
    """Экспортер метрик в формате Prometheus"""
    
    def __init__(self):
        """Инициализация экспортера метрик"""
        self.metrics_cache = {}
    
    def record_ping_result(self, device_ip: str, device_description: str, 
                          is_alive: bool, response_time: float = None, 
                          packet_loss: float = 0.0):
        """
        Запись результатов ping в метрики Prometheus
        
        Args:
            device_ip: IP-адрес устройства
            device_description: Описание устройства
            is_alive: Доступность устройства
            response_time: Время отклика в миллисекундах
            packet_loss: Процент потери пакетов
        """
        
        # Записываем ping запрос
        status = "success" if is_alive else "failed"
        ping_requests_total.labels(device_ip=device_ip, status=status).inc()
        
        # Записываем время отклика, если доступно
        if response_time is not None:
            ping_response_time.labels(device_ip=device_ip).observe(response_time / 1000.0)  # Конвертируем в секунды
        
        # Записываем доступность
        availability_value = 1.0 if is_alive else 0.0
        device_availability.labels(
            device_ip=device_ip, 
            device_description=device_description
        ).set(availability_value)
        
        # Записываем потерю пакетов
        packet_loss_percentage.labels(device_ip=device_ip).set(packet_loss)
    
    def get_metrics(self) -> str:
        """Получение метрик в текстовом формате Prometheus"""
        return generate_latest()
    
    def get_metrics_headers(self) -> Dict[str, str]:
        """Получение заголовков для endpoint метрик"""
        return {'Content-Type': CONTENT_TYPE_LATEST}

# Глобальный экземпляр экспортера метрик
metrics_exporter = MetricsExporter() 