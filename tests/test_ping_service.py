import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from app.ping_service import PingService


class TestPingService:

    @pytest.fixture
    def ping_service(self):
        return PingService(timeout=5, count=3)

    @pytest.mark.asyncio
    async def test_ping_device_success(self, ping_service):
        """Test successful ping to a device"""
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            # Mock successful ping response
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (
                b"PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.\n"
                b"64 bytes from 8.8.8.8: icmp_seq=1 time=10.1 ms\n"
                b"64 bytes from 8.8.8.8: icmp_seq=2 time=9.8 ms\n"
                b"64 bytes from 8.8.8.8: icmp_seq=3 time=10.2 ms\n\n"
                b"--- 8.8.8.8 ping statistics ---\n"
                b"3 packets transmitted, 3 received, 0% packet loss, time 2002ms\n"
                b"rtt min/avg/max/mdev = 9.800/10.033/10.200/0.200 ms",
                b"",
            )
            mock_subprocess.return_value = mock_process

            result = await ping_service.ping_device("8.8.8.8")

            assert result["is_alive"] is True
            assert result["response_time"] is not None
            assert result["packet_loss"] == 0.0
            assert result["error_message"] is None

    @pytest.mark.asyncio
    async def test_ping_device_failure(self, ping_service):
        """Test failed ping to a device"""
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            # Mock failed ping response
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate.return_value = (
                b"",
                b"ping: connect: Network is unreachable",
            )
            mock_subprocess.return_value = mock_process

            result = await ping_service.ping_device("192.168.1.999")

            assert result["is_alive"] is False
            assert result["response_time"] is None
            assert result["packet_loss"] == 100.0
            assert "Network is unreachable" in result[
                "error_message"
            ]

    @pytest.mark.asyncio
    async def test_ping_device_timeout(self, ping_service):
        """Test ping timeout"""
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            # Mock timeout
            mock_subprocess.side_effect = asyncio.TimeoutError()

            result = await ping_service.ping_device("8.8.8.8")

            assert result["is_alive"] is False
            assert result["response_time"] is None
            assert result["packet_loss"] == 100.0
            assert result["error_message"] == "Ping timeout"

    def test_parse_unix_ping_output_success(self, ping_service):
        """Test parsing successful Unix ping output"""
        output = """PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.
64 bytes from 8.8.8.8: icmp_seq=1 time=10.1 ms
64 bytes from 8.8.8.8: icmp_seq=2 time=9.8 ms
64 bytes from 8.8.8.8: icmp_seq=3 time=10.2 ms

--- 8.8.8.8 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2002ms
rtt min/avg/max/mdev = 9.800/10.033/10.200/0.200 ms"""

        result = ping_service._parse_unix_ping_output(output)

        assert result["is_alive"] is True
        assert abs(result["response_time"] - 10.033) < 0.1
        assert result["packet_loss"] == 0.0
        assert result["error_message"] is None

    def test_parse_unix_ping_output_failure(self, ping_service):
        """Test parsing failed Unix ping output"""
        output = """PING 192.168.1.999 (192.168.1.999) 56(84) bytes of data.

--- 192.168.1.999 ping statistics ---
3 packets transmitted, 0 received, 100% packet loss, time 3000ms"""

        result = ping_service._parse_unix_ping_output(output)

        assert result["is_alive"] is False
        assert result["response_time"] is None
        assert result["packet_loss"] == 100.0
        assert "No response received" in result[
            "error_message"
        ]

    def test_parse_windows_ping_output_success(self, ping_service):
        """Test parsing successful Windows ping output"""
        output = """Pinging 8.8.8.8 with 32 bytes of data:
Reply from 8.8.8.8: bytes=32 time=10ms TTL=113
Reply from 8.8.8.8: bytes=32 time=9ms TTL=113
Reply from 8.8.8.8: bytes=32 time=11ms TTL=113

Ping statistics for 8.8.8.8:
    Packets: Sent = 3, Received = 3, Lost = 0 (0% loss),
Approximate round trip times in milli-seconds:
    Minimum = 9ms, Maximum = 11ms, Average = 10ms"""

        result = ping_service._parse_windows_ping_output(output)

        assert result["is_alive"] is True
        assert abs(result["response_time"] - 10.0) < 0.1
        assert result["packet_loss"] == 0.0
        assert result["error_message"] is None

    def test_parse_windows_ping_output_failure(self, ping_service):
        """Test parsing failed Windows ping output"""
        output = """Pinging 192.168.1.999 with 32 bytes of data:
Request timed out.
Request timed out.
Request timed out.

Ping statistics for 192.168.1.999:
    Packets: Sent = 3, Received = 0, Lost = 3 (100% loss),"""

        result = ping_service._parse_windows_ping_output(output)

        assert result["is_alive"] is False
        assert result["response_time"] is None
        assert result["packet_loss"] == 100.0
        assert "No response received" in result[
            "error_message"
        ]
