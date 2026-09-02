import asyncio
import logging
from pathlib import Path

import uvicorn

from app.api import create_api
from app.buffer import EventBuffer
from app.config import Settings
from app.database import create_session_factory
from app.rfid import AggregatedTagRead
from app.tag_read_repository import TagReadRepository
from app.tcp_server import TcpReceiver

settings = Settings()
session_factory = create_session_factory(settings)
app = create_api(settings, session_factory)
tag_read_repository = TagReadRepository(session_factory, settings.duplicate_window_ms)
event_buffer = EventBuffer(Path(settings.data_dir) / "pending-tag-reads.jsonl")


async def log_tag_read(tag_read: AggregatedTagRead) -> None:
    try:
        await asyncio.to_thread(tag_read_repository.save, tag_read)
    except Exception:
        logging.getLogger(__name__).exception("Could not persist RFID event from reader_id=%s", tag_read.event.reader_id)
        await asyncio.to_thread(event_buffer.append, tag_read)


async def main() -> None:
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        replayed = await asyncio.to_thread(event_buffer.replay, tag_read_repository.save)
        if replayed:
            logging.getLogger(__name__).info("Replayed %s buffered RFID events", replayed)
    except Exception:
        logging.getLogger(__name__).exception("Could not replay buffered RFID events")
    receiver = TcpReceiver(
        settings.tcp_host,
        settings.tcp_port,
        settings.duplicate_window_ms,
        log_tag_read,
    )
    web_server = uvicorn.Server(
        uvicorn.Config(app, host=settings.api_host, port=settings.api_port, log_level=settings.log_level.lower())
    )
    async with asyncio.TaskGroup() as task_group:
        task_group.create_task(receiver.serve_forever())
        task_group.create_task(web_server.serve())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass