import asyncio
import logging
from collections.abc import Awaitable, Callable

from app.adapters import ReceiverType
from app.rfid import AggregatedTagRead, DuplicateAggregator, parse_simulator_event

logger = logging.getLogger(__name__)
TagReadHandler = Callable[[AggregatedTagRead], Awaitable[None]]


class TcpReceiver:
    receiver_type = ReceiverType.SIMULATED

    def __init__(self, host: str, port: int, duplicate_window_ms: int, on_tag_read: TagReadHandler) -> None:
        self.host = host
        self.port = port
        self.on_tag_read = on_tag_read
        self.aggregator = DuplicateAggregator(duplicate_window_ms)

    async def start(self) -> asyncio.AbstractServer:
        return await asyncio.start_server(self._handle_connection, self.host, self.port)

    async def serve_forever(self, retry_delay_seconds: float = 1.0) -> None:
        while True:
            try:
                server = await self.start()
                async with server:
                    await server.serve_forever()
            except asyncio.CancelledError:
                raise
            except OSError:
                logger.exception("TCP receiver stopped; retrying")
                await asyncio.sleep(retry_delay_seconds)

    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer = writer.get_extra_info("peername")
        reader_ip = peer[0] if peer else "unknown"
        try:
            while payload := await reader.readline():
                if len(payload) > 65_536:
                    logger.warning("Discarded oversize RFID event from %s", reader_ip)
                    continue
                try:
                    event = parse_simulator_event(payload.decode("utf-8").strip(), reader_ip)
                    await self.on_tag_read(self.aggregator.process(event))
                except (UnicodeDecodeError, ValueError):
                    logger.warning("Discarded invalid RFID event from %s", reader_ip, exc_info=True)
        except (ConnectionError, asyncio.IncompleteReadError):
            logger.info("RFID connection closed by %s", reader_ip)
        finally:
            writer.close()
            await writer.wait_closed()