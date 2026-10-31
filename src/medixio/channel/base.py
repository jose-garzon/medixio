from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol


@dataclass
class Inbound:
    jid: str  # chat address used to reply and for proactive messages
    text: str
    image: bytes | None = None  # in memory only, never persisted
    image_media_type: str | None = None


InboundHandler = Callable[[Inbound], Awaitable[str | None]]


class Channel(Protocol):
    async def send_text(self, jid: str, text: str) -> None: ...

    async def run(self, on_message: InboundHandler) -> None: ...


class RecordingChannel:
    """In-memory channel for tests and the admin chat endpoint."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_text(self, jid: str, text: str) -> None:
        self.sent.append((jid, text))

    async def run(self, on_message: InboundHandler) -> None:
        return None
