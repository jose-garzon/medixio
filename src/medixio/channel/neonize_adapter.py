import asyncio
import logging
from pathlib import Path

from neonize.aioze.client import NewAClient
from neonize.aioze.events import (
    ConnectedEv,
    DisconnectedEv,
    LoggedOutEv,
    MessageEv,
    StreamReplacedEv,
    TemporaryBanEv,
)
from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import Message
from neonize.utils.jid import Jid2String, build_jid

from medixio.channel.base import Inbound, InboundHandler
from medixio.observability import obs


log = logging.getLogger(__name__)


def _jid_from_string(jid: str):  # type: ignore[no-untyped-def]
    user, _, server = jid.partition("@")
    return build_jid(user.split(":", 1)[0], server or "s.whatsapp.net")


_WRAPPERS = (
    "ephemeralMessage",
    "viewOnceMessage",
    "viewOnceMessageV2",
    "viewOnceMessageV2Extension",
    "documentWithCaptionMessage",
)
_DOCUMENT_TYPES = ("image/jpeg", "image/png", "image/webp", "image/gif")


def _unwrap(msg: Message) -> Message:
    """Disappearing, view-once and captioned-document messages nest the real one."""
    for _ in range(3):
        for name in _WRAPPERS:
            if msg.HasField(name):
                msg = getattr(msg, name).message
                break
        else:
            return msg
    return msg


def _readable_document(mimetype: str) -> bool:
    """Images sent as files ("documento") are as readable as photos."""
    return mimetype.split(";")[0].strip() in _DOCUMENT_TYPES


class NeonizeChannel:
    """Unofficial WhatsApp multi-device client. Pair once by scanning the QR in logs."""

    def __init__(self, session_db: str) -> None:
        Path(session_db).parent.mkdir(parents=True, exist_ok=True)
        self.client = NewAClient(session_db)
        self.connected = asyncio.Event()

    async def send_text(self, jid: str, text: str) -> None:
        with obs().timer("whatsapp.send", source="proactive"):
            await self.client.send_message(_jid_from_string(jid), text)

    async def run(self, on_message: InboundHandler) -> None:
        @self.client.event(ConnectedEv)  # type: ignore[untyped-decorator]
        async def _on_connected(_: NewAClient, __: ConnectedEv) -> None:
            log.info("whatsapp connected")
            obs().metric("whatsapp.connected", 1)
            self.connected.set()

        @self.client.event(DisconnectedEv)  # type: ignore[untyped-decorator]
        async def _on_disconnected(_: NewAClient, __: DisconnectedEv) -> None:
            log.warning("whatsapp disconnected")
            self.connected.clear()

        @self.client.event(LoggedOutEv)  # type: ignore[untyped-decorator]
        async def _on_logged_out(_: NewAClient, __: LoggedOutEv) -> None:
            log.error("whatsapp logged out: re-pair by scanning a new QR")
            self.connected.clear()

        @self.client.event(StreamReplacedEv)  # type: ignore[untyped-decorator]
        async def _on_replaced(_: NewAClient, __: StreamReplacedEv) -> None:
            log.error("whatsapp session opened elsewhere (stream replaced)")
            self.connected.clear()

        @self.client.event(TemporaryBanEv)  # type: ignore[untyped-decorator]
        async def _on_ban(_: NewAClient, event: TemporaryBanEv) -> None:
            log.critical("whatsapp TEMPORARY BAN: %s", event)
            self.connected.clear()

        @self.client.event(MessageEv)  # type: ignore[untyped-decorator]
        async def _on_message(client: NewAClient, event: MessageEv) -> None:
            source = event.Info.MessageSource
            if source.IsFromMe or source.IsGroup:
                return
            msg = _unwrap(event.Message)
            text = msg.conversation or msg.extendedTextMessage.text
            image: bytes | None = None
            media_type: str | None = None
            if msg.HasField("imageMessage"):
                text = msg.imageMessage.caption or text
                media_type = msg.imageMessage.mimetype or "image/jpeg"
            elif msg.HasField("documentMessage") and _readable_document(
                msg.documentMessage.mimetype
            ):
                text = msg.documentMessage.caption or text
                media_type = msg.documentMessage.mimetype.split(";")[0]
            if media_type is not None:
                # bytes, no path => not written to disk
                data = await client.download_any(msg)
                image = data if isinstance(data, bytes) else None
            if not text and image is None:
                kinds = [f.name for f, _ in msg.ListFields()]
                log.info("ignored inbound message kinds=%s", kinds)
                return
            jid = Jid2String(source.Chat)
            log.info(
                "inbound jid=%s len=%d image=%s", jid, len(text), image is not None
            )
            obs().metric("whatsapp.inbound", 1, image=image is not None)
            try:
                reply = await on_message(
                    Inbound(
                        jid=jid, text=text, image=image, image_media_type=media_type
                    )
                )
            finally:
                image = None  # drop image bytes as soon as handled
            if reply:
                with obs().timer("whatsapp.send", source="reply"):
                    await client.send_message(source.Chat, reply)

        await self.client.connect()
        await self.client.idle()
