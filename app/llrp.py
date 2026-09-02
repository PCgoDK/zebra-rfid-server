import asyncio
import math
import struct
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
import logging

from app.adapters import ReceiverType
from app.rfid import AggregatedTagRead, DuplicateAggregator, TagEvent

logger = logging.getLogger(__name__)

RO_ACCESS_REPORT = 61
KEEPALIVE = 62
KEEPALIVE_ACK = 72
PARAM_TAG_REPORT_DATA = 240
PARAM_EPC_DATA = 241
MAX_FRAME_LENGTH = 65_536

TV_PARAMETER_LENGTHS = {
    1: 2,
    2: 8,
    3: 8,
    4: 8,
    5: 8,
    6: 1,
    7: 2,
    8: 2,
    9: 4,
    10: 2,
    11: 2,
    12: 2,
    13: 12,
    14: 2,
}

TagReadHandler = Callable[[AggregatedTagRead], Awaitable[None]]


def get_message_type(frame: bytes) -> int | None:
    if len(frame) < 10:
        return None
    return struct.unpack("!H", frame[:2])[0] & 0x03FF


def get_message_id(frame: bytes) -> int | None:
    if len(frame) < 10:
        return None
    return struct.unpack("!I", frame[6:10])[0]


def build_message(message_type: int, message_id: int, payload: bytes = b"") -> bytes:
    version_and_type = (1 << 10) | (message_type & 0x03FF)
    return struct.pack("!HII", version_and_type, 10 + len(payload), message_id) + payload


def parse_parameters(data: bytes) -> list[tuple[str, int, bytes]]:
    parameters: list[tuple[str, int, bytes]] = []
    index = 0
    while index < len(data):
        first_byte = data[index]
        if first_byte & 0x80:
            parameter_type = first_byte & 0x7F
            value_length = TV_PARAMETER_LENGTHS.get(parameter_type)
            if value_length is None or index + 1 + value_length > len(data):
                break
            parameters.append(("tv", parameter_type, data[index + 1 : index + 1 + value_length]))
            index += 1 + value_length
            continue
        if index + 4 > len(data):
            break
        parameter_type = struct.unpack("!H", data[index : index + 2])[0] & 0x03FF
        total_length = struct.unpack("!H", data[index + 2 : index + 4])[0]
        if total_length < 4 or index + total_length > len(data):
            break
        parameters.append(("tlv", parameter_type, data[index + 4 : index + total_length]))
        index += total_length
    return parameters


def parse_ro_access_report(frame: bytes, reader_id: int, reader_ip: str) -> list[TagEvent]:
    if len(frame) < 10 or struct.unpack("!I", frame[2:6])[0] != len(frame):
        return []
    if get_message_type(frame) != RO_ACCESS_REPORT:
        return []
    events: list[TagEvent] = []
    for encoding, parameter_type, value in parse_parameters(frame[10:]):
        if encoding != "tlv" or parameter_type != PARAM_TAG_REPORT_DATA:
            continue
        event = parse_tag_report(value, reader_id, reader_ip)
        if event is not None:
            events.append(event)
    return events


def parse_tag_report(data: bytes, reader_id: int, reader_ip: str) -> TagEvent | None:
    epc_hex: str | None = None
    antenna: int | None = None
    rssi: float | None = None
    reader_timestamp: datetime | None = None
    for encoding, parameter_type, value in parse_parameters(data):
        if encoding == "tlv" and parameter_type == PARAM_EPC_DATA and len(value) >= 2:
            bit_length = struct.unpack("!H", value[:2])[0]
            byte_length = math.ceil(bit_length / 8)
            if len(value) >= 2 + byte_length:
                epc_hex = value[2 : 2 + byte_length].hex().upper()
        elif encoding == "tv" and parameter_type == 13 and len(value) == 12:
            epc_hex = value.hex().upper()
        elif encoding == "tv" and parameter_type == 1 and len(value) == 2:
            antenna = struct.unpack("!H", value)[0]
        elif encoding == "tv" and parameter_type in (2, 4) and len(value) == 8:
            reader_timestamp = datetime.fromtimestamp(struct.unpack("!Q", value)[0] / 1_000_000, tz=timezone.utc)
        elif encoding == "tv" and parameter_type == 6 and len(value) == 1:
            rssi = float(struct.unpack("!b", value)[0])
    if epc_hex is None:
        return None
    return TagEvent(
        reader_id=reader_id,
        epc_hex=epc_hex,
        antenna=antenna,
        reader_ip=reader_ip,
        rssi=rssi,
        reader_timestamp=reader_timestamp,
        raw_payload=data.hex(),
    )


class LLRPReceiver:
    receiver_type = ReceiverType.LLRP

    def __init__(self, host: str, port: int, reader_id: int, duplicate_window_ms: int, on_tag_read: TagReadHandler) -> None:
        self.host = host
        self.port = port
        self.reader_id = reader_id
        self.on_tag_read = on_tag_read
        self.aggregator = DuplicateAggregator(duplicate_window_ms)

    async def serve_forever(self, retry_delay_seconds: float = 2.0) -> None:
        while True:
            try:
                reader, writer = await asyncio.open_connection(self.host, self.port)
                await self.consume(reader, writer)
            except asyncio.CancelledError:
                raise
            except OSError:
                logger.exception("LLRP reader connection failed for %s; retrying", self.host)
            await asyncio.sleep(retry_delay_seconds)

    async def consume(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            while True:
                header = await reader.readexactly(10)
                frame_length = struct.unpack("!I", header[2:6])[0]
                if frame_length < 10 or frame_length > MAX_FRAME_LENGTH:
                    raise ValueError(f"Invalid LLRP frame length: {frame_length}")
                frame = header + await reader.readexactly(frame_length - 10)
                if get_message_type(frame) == KEEPALIVE:
                    message_id = get_message_id(frame)
                    if message_id is not None:
                        writer.write(build_message(KEEPALIVE_ACK, message_id))
                        await writer.drain()
                    continue
                for event in parse_ro_access_report(frame, self.reader_id, self.host):
                    await self.on_tag_read(self.aggregator.process(event))
        except asyncio.IncompleteReadError:
            logger.warning("LLRP reader closed connection: %s", self.host)
        finally:
            writer.close()
            await writer.wait_closed()