from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlmodel import Session, func, select

from medixio import knowledge
from medixio.channel.base import Inbound
from medixio.config import get_settings
from medixio.db import get_session
from medixio.handler import handle
from medixio.modules.patients.models import Patient
from medixio.observability.routes import router as obs_router
from medixio.scheduler import dispatch_due
from medixio.shared.time import utcnow


router = APIRouter()
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/health")
def health(session: SessionDep, request: Request) -> dict[str, Any]:
    session.connection().execute(text("SELECT 1"))
    channel = getattr(request.app.state, "channel", None)
    connected = getattr(channel, "connected", None)
    return {
        "status": "ok",
        "whatsapp": "connected" if connected and connected.is_set() else "disconnected",
    }


def require_admin(
    x_admin_token: Annotated[str | None, Header()] = None,
    token: Annotated[str | None, Query()] = None,
) -> None:
    """Header for scripts; `?token=` so the dashboard opens in a browser."""
    expected = get_settings().admin_token
    if expected and expected not in (x_admin_token, token):
        raise HTTPException(status_code=401)


admin = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])
admin.include_router(obs_router)


class ChatIn(BaseModel):
    jid: str
    text: str


@admin.post("/chat")
async def chat(body: ChatIn) -> dict[str, str | None]:
    """Talk to the bot as a given WhatsApp JID, without WhatsApp."""
    return {"reply": await handle(Inbound(jid=body.jid, text=body.text))}


@admin.get("/patients")
def list_patients(session: SessionDep) -> dict[str, int]:
    total = session.exec(select(func.count()).select_from(Patient)).one()
    return {"patients": total}


@admin.get("/knowledge/unreviewed")
def unreviewed() -> list[dict[str, Any]]:
    return knowledge.unreviewed()


@admin.post("/reminders/dispatch")
async def dispatch(session: SessionDep, request: Request) -> dict[str, int]:
    channel = request.app.state.channel
    if channel is None:
        raise HTTPException(status_code=503, detail="no channel")
    return {"sent": await dispatch_due(session, channel, utcnow())}
