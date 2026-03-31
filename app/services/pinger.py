import asyncio
import logging
import struct
import socket
import time
import os

logger = logging.getLogger(__name__)


def _checksum(data: bytes) -> int:
    s = 0
    n = len(data) % 2
    for i in range(0, len(data) - n, 2):
        s += (data[i]) + ((data[i + 1]) << 8)
    if n:
        s += data[-1]
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
    s = ~s & 0xFFFF
    return s


async def ping_host(host: str, timeout: float = 2.0) -> tuple[bool, float | None]:
    """Ping a host via ICMP. Returns (is_up, latency_ms)."""
    loop = asyncio.get_event_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, _sync_ping, host, timeout),
            timeout=timeout + 1,
        )
    except (asyncio.TimeoutError, Exception) as e:
        logger.debug("Ping to %s failed: %s", host, e)
        return False, None


def _sync_ping(host: str, timeout: float) -> tuple[bool, float | None]:
    """Synchronous ICMP ping implementation."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    except PermissionError:
        # Fallback: use DGRAM socket (works on macOS without root)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_ICMP)
        except OSError:
            logger.warning("Cannot create ICMP socket. Running ping via subprocess for %s", host)
            return _subprocess_ping(host, timeout)

    sock.settimeout(timeout)
    packet_id = os.getpid() & 0xFFFF
    seq = 1

    # Build ICMP echo request
    header = struct.pack("!BBHHH", 8, 0, 0, packet_id, seq)
    payload = b"uptime-monitor-ping"
    chk = _checksum(header + payload)
    header = struct.pack("!BBHHH", 8, 0, chk, packet_id, seq)
    packet = header + payload

    try:
        start = time.perf_counter()
        sock.sendto(packet, (host, 0))
        sock.recv(1024)
        latency = (time.perf_counter() - start) * 1000
        return True, round(latency, 2)
    except (socket.timeout, OSError):
        return False, None
    finally:
        sock.close()


def _subprocess_ping(host: str, timeout: float) -> tuple[bool, float | None]:
    """Fallback ping using system ping command."""
    import subprocess

    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", str(int(timeout)), host],
            capture_output=True,
            text=True,
            timeout=timeout + 2,
        )
        if result.returncode == 0:
            # Parse latency from output
            for line in result.stdout.splitlines():
                if "time=" in line:
                    time_part = line.split("time=")[1].split()[0]
                    return True, round(float(time_part), 2)
            return True, None
        return False, None
    except (subprocess.TimeoutExpired, Exception):
        return False, None


async def ping_host_with_retry(host: str, timeout: float = 2.0, retries: int = 3) -> tuple[bool, float | None]:
    """Ping with retry logic. Only declares down after all retries fail."""
    for attempt in range(retries):
        is_up, latency = await ping_host(host, timeout)
        if is_up:
            return True, latency
        if attempt < retries - 1:
            await asyncio.sleep(0.5)
    return False, None


async def ping_batch(hosts: list[tuple[str, str]], timeout: float = 2.0, retries: int = 3) -> dict[str, tuple[bool, float | None]]:
    """Ping multiple hosts concurrently. hosts is list of (server_id, ip_address)."""
    tasks = {
        server_id: ping_host_with_retry(ip, timeout, retries)
        for server_id, ip in hosts
    }
    results = {}
    for server_id, coro in tasks.items():
        results[server_id] = await coro
    return results
