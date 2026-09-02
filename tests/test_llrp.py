import asyncio
import struct

from app.llrp import (
    KEEPALIVE,
    KEEPALIVE_ACK,
    PARAM_EPC_DATA,
    PARAM_TAG_REPORT_DATA,
    RO_ACCESS_REPORT,
    LLRPReceiver,
    build_message,
    get_message_id,
    get_message_type,
    parse_ro_access_report,
)


def build_tlv(parameter_type: int, value: bytes) -> bytes:
    return struct.pack("!HH", parameter_type, len(value) + 4) + value


def build_tv(parameter_type: int, value: bytes) -> bytes:
    return bytes([0x80 | parameter_type]) + value


def test_parse_ro_access_report_extracts_tag_data() -> None:
    epc = bytes.fromhex("E2000017221101441890ABCD")
    tag_report = build_tlv(
        PARAM_TAG_REPORT_DATA,
        build_tlv(PARAM_EPC_DATA, struct.pack("!H", len(epc) * 8) + epc)
        + build_tv(1, struct.pack("!H", 2))
        + build_tv(6, struct.pack("!b", -45)),
    )

    events = parse_ro_access_report(build_message(RO_ACCESS_REPORT, 1, tag_report), 7, "192.0.2.10")

    assert len(events) == 1
    assert events[0].reader_id == 7
    assert events[0].epc_hex == "E2000017221101441890ABCD"
    assert events[0].antenna == 2
    assert events[0].rssi == -45


def test_llrp_receiver_acknowledges_keepalive() -> None:
    async def scenario() -> None:
        received = []

        async def collect(tag_read) -> None:
            received.append(tag_read)

        receiver = LLRPReceiver("192.0.2.10", 5084, 7, 1000, collect)
        server_side, client_side = await asyncio.open_connection(*await start_test_server(receiver))
        try:
            client_side.write(build_message(KEEPALIVE, 123))
            await client_side.drain()
            ack = await server_side.readexactly(10)
        finally:
            client_side.close()
            await client_side.wait_closed()

        assert get_message_type(ack) == KEEPALIVE_ACK
        assert get_message_id(ack) == 123
        assert received == []

    asyncio.run(scenario())


async def start_test_server(receiver: LLRPReceiver) -> tuple[str, int]:
    async def handle_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await receiver.consume(reader, writer)

    server = await asyncio.start_server(handle_connection, "127.0.0.1", 0)
    host, port = server.sockets[0].getsockname()[:2]
    return host, port