import asyncio
import re
import platform
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class PingService:
    """Сервис для выполнения ping операций на сетевых устройствах"""

    def __init__(self, timeout: int = 5, count: int = 3):
        """
        Инициализация ping сервиса

        Args:
            timeout: Таймаут в секундах
            count: Количество пакетов для отправки
        """
        self.timeout = timeout
        self.count = count
        self.system = (
            platform.system().lower()
        )  # Определяем операционную систему

    async def ping_device(self, ip_address: str) -> Dict:
        """
        Выполнение ping устройства и возврат результатов

        Args:
            ip_address: IP-адрес устройства для проверки

        Returns:
            Dict с ключами: is_alive, response_time, packet_loss, error_message
        """
        try:
            # Выбираем реализацию ping в зависимости от ОС
            if self.system == "windows":
                result = await self._ping_windows(ip_address)
            else:
                result = await self._ping_unix(ip_address)

            return result
        except Exception as e:
            logger.error(f"Error pinging {ip_address}: {str(e)}")
            return {
                "is_alive": False,
                "response_time": None,
                "packet_loss": 100.0,
                "error_message": str(e),
            }

    async def _ping_windows(self, ip_address: str) -> Dict:
        """Реализация ping для Windows"""
        # Команда ping для Windows: -n количество, -w таймаут в миллисекундах
        cmd = [
            "ping",
            "-n",
            str(self.count),
            "-w",
            str(self.timeout * 1000),
            ip_address,
        ]

        try:
            # Создаем асинхронный процесс
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.timeout + 5
            )

            # Проверяем код возврата
            if process.returncode != 0:
                return {
                    "is_alive": False,
                    "response_time": None,
                    "packet_loss": 100.0,
                    "error_message": (
                        stderr.decode() if stderr else "Ping failed"
                    ),
                }

            # Парсим результат
            output = stdout.decode()
            return self._parse_windows_ping_output(output)

        except asyncio.TimeoutError:
            return {
                "is_alive": False,
                "response_time": None,
                "packet_loss": 100.0,
                "error_message": "Ping timeout",
            }

    async def _ping_unix(self, ip_address: str) -> Dict:
        """Реализация ping для Unix-подобных систем (Linux, macOS)"""
        # Команда ping для Unix: -c количество, -W таймаут в секундах
        cmd = [
            "ping",
            "-c",
            str(self.count),
            "-W",
            str(self.timeout),
            ip_address,
        ]

        try:
            # Создаем асинхронный процесс
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.timeout + 5
            )

            # Проверяем код возврата
            if process.returncode != 0:
                return {
                    "is_alive": False,
                    "response_time": None,
                    "packet_loss": 100.0,
                    "error_message": (
                        stderr.decode() if stderr else "Ping failed"
                    ),
                }

            # Парсим результат
            output = stdout.decode()
            return self._parse_unix_ping_output(output)

        except asyncio.TimeoutError:
            return {
                "is_alive": False,
                "response_time": None,
                "packet_loss": 100.0,
                "error_message": "Ping timeout",
            }

    def _parse_windows_ping_output(self, output: str) -> Dict:
        """Парсинг вывода ping для Windows"""
        # Проверяем, был ли ping успешным (есть ли TTL=)
        if "TTL=" not in output:
            return {
                "is_alive": False,
                "response_time": None,
                "packet_loss": 100.0,
                "error_message": "No response received",
            }

        # Извлекаем времена отклика (формат: time=10ms или time<10ms)
        time_pattern = r"time[=<](\d+)ms"
        times = re.findall(time_pattern, output)

        if not times:
            return {
                "is_alive": False,
                "response_time": None,
                "packet_loss": 100.0,
                "error_message": "Could not parse response times",
            }

        # Вычисляем среднее время отклика
        response_times = [float(t) for t in times]
        avg_response_time = sum(response_times) / len(response_times)

        # Вычисляем потерю пакетов
        sent_pattern = r"Sent = (\d+)"
        received_pattern = r"Received = (\d+)"

        sent_match = re.search(sent_pattern, output)
        received_match = re.search(received_pattern, output)

        if sent_match and received_match:
            sent = int(sent_match.group(1))
            received = int(received_match.group(1))
            packet_loss = ((sent - received) / sent) * 100
        else:
            packet_loss = 0.0

        return {
            "is_alive": True,
            "response_time": avg_response_time,
            "packet_loss": packet_loss,
            "error_message": None,
        }

    def _parse_unix_ping_output(self, output: str) -> Dict:
        """Парсинг вывода ping для Unix-систем"""
        # Проверяем, был ли ping успешным (есть ли time=)
        if "time=" not in output:
            return {
                "is_alive": False,
                "response_time": None,
                "packet_loss": 100.0,
                "error_message": "No response received",
            }

        # Извлекаем времена отклика (формат: time=10.1 ms)
        time_pattern = r"time=(\d+\.?\d*)"
        times = re.findall(time_pattern, output)

        if not times:
            return {
                "is_alive": False,
                "response_time": None,
                "packet_loss": 100.0,
                "error_message": "Could not parse response times",
            }

        # Вычисляем среднее время отклика
        response_times = [float(t) for t in times]
        avg_response_time = sum(response_times) / len(response_times)

        # Извлекаем потерю пакетов из итоговой статистики
        loss_pattern = r"(\d+)% packet loss"
        loss_match = re.search(loss_pattern, output)
        packet_loss = float(loss_match.group(1)) if loss_match else 0.0

        return {
            "is_alive": True,
            "response_time": avg_response_time,
            "packet_loss": packet_loss,
            "error_message": None,
        }
