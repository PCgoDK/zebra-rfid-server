import asyncio

import pytest

from app.discovery import ReaderDiscovery, ReaderStatus, validate_reader_ip


def test_validate_reader_ip_normalizes_valid_ipv4_address() -> None:
    assert validate_reader_ip("192.168.1.15") == "192.168.1.15"


@pytest.mark.parametrize("address", ["not-an-ip", "::1", "0.0.0.0", "224.0.0.1", "192.168.001.015"])
def test_validate_reader_ip_rejects_invalid_or_unsafe_addresses(address: str) -> None:
    with pytest.raises(ValueError):
        validate_reader_ip(address)


def test_discovery_only_reports_read_only_probe_results() -> None:
    probed_addresses = []

    async def probe(address: str) -> bool:
        probed_addresses.append(address)
        return address == "192.168.1.15"

    readers = asyncio.run(ReaderDiscovery(probe).discover(["192.168.1.15", "192.168.1.82", "192.168.1.15"]))

    assert probed_addresses == ["192.168.1.15", "192.168.1.82"]
    assert [(reader.ip_address, reader.status) for reader in readers] == [
        ("192.168.1.15", ReaderStatus.CONNECTED_WITHOUT_DATA),
        ("192.168.1.82", ReaderStatus.OFFLINE),
    ]