from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from enum import StrEnum

from app.rfid import AggregatedTagRead

TagReadHandler = Callable[[AggregatedTagRead], Awaitable[None]]


class ReceiverType(StrEnum):
    TCP = "tcp"
    LLRP = "llrp"
    ZEBRA_EVENT = "zebra_event"
    SIMULATED = "simulated"


class RfidReceiverAdapter(ABC):
    receiver_type: ReceiverType

    @abstractmethod
    async def serve_forever(self, on_tag_read: TagReadHandler) -> None:
        """Receive tag reads and pass them to the application handler."""