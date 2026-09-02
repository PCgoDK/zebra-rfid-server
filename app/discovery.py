import asyncio
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum
from ipaddress import IPv4Address, ip_address


class ReaderStatus(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    RECEIVING_DATA = "receiving_data"
    CONNECTED_WITHOUT_DATA = "connected_without_data"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DiscoveredReader:
    ip_address: str
    status: ReaderStatus
    model: str | None = None
    firmware_version: str | None = None
    serial_number: str | None = None
    mac_address: str | None = None


Probe = Callable[[str], Awaitable[bool]]


def validate_reader_ip(value: str) -> str:
    parsed = ip_address(value)
    if not isinstance(parsed, IPv4Address):
        raise ValueError("Reader IP address must be IPv4")
    if parsed.is_unspecified or parsed.is_multicast:
        raise ValueError("Reader IP address must be a unicast address")
    return str(parsed)


async def probe_llrp(ip: str, port: int = 5084, timeout_seconds: float = 1.0) -> bool:
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout_seconds)
    except (OSError, TimeoutError):
        return False
    writer.close()
    await writer.wait_closed()
    return True


class ReaderDiscovery:
    def __init__(self, probe: Probe = probe_llrp) -> None:
        self.probe = probe

    async def discover(self, addresses: Iterable[str]) -> list[DiscoveredReader]:
        validated_addresses = list(dict.fromkeys(validate_reader_ip(address) for address in addresses))
        online = await asyncio.gather(*(self.probe(address) for address in validated_addresses))
        return [
            DiscoveredReader(
                ip_address=address,
                status=ReaderStatus.CONNECTED_WITHOUT_DATA if is_online else ReaderStatus.OFFLINE,
            )
            for address, is_online in zip(validated_addresses, online, strict=True)
        ]