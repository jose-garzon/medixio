import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from sqlmodel import Session, select

from medixio import handler, ratelimit
from medixio.channel.base import Inbound
from medixio.config import get_settings
from medixio.modules.patients.models import Patient
from medixio.observability import obs


def _model() -> FunctionModel:
    def fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart("ok")])

    return FunctionModel(fn)


@pytest.fixture(autouse=True)
def _fake_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(handler, "get_model", _model)


@pytest.mark.asyncio
async def test_burst_gets_one_notice_then_silence(
    patient: Patient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "rate_msgs_per_10min", 3)
    jid = patient.whatsapp_jid
    replies = [await handler.handle(Inbound(jid=jid, text="hola")) for _ in range(6)]
    assert replies[:3] == ["ok", "ok", "ok"]
    assert replies[3] == ratelimit.MSG_NOTICE
    assert replies[4:] == [None, None]


@pytest.mark.asyncio
async def test_images_capped_per_day(
    patient: Patient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "rate_images_per_day", 0)
    reply = await handler.handle(
        Inbound(
            jid=patient.whatsapp_jid, text="", image=b"x", image_media_type="image/jpeg"
        )
    )
    assert reply == ratelimit.IMG_NOTICE


@pytest.mark.asyncio
async def test_token_budget_blocks_everyone(
    patient: Patient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "daily_token_budget", 1000)
    obs().metric("agent.tokens_in", 1500)
    reply = await handler.handle(Inbound(jid=patient.whatsapp_jid, text="hola"))
    assert reply == ratelimit.BUDGET_NOTICE


@pytest.mark.asyncio
async def test_signup_cap_ignores_new_numbers(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "rate_signups_per_hour", 1)
    first = await handler.handle(Inbound(jid="571@s.whatsapp.net", text="hola"))
    second = await handler.handle(Inbound(jid="572@s.whatsapp.net", text="hola"))
    assert first == handler.CONSENT_TEXT
    assert second is None
    assert len(session.exec(select(Patient)).all()) == 1


@pytest.mark.asyncio
async def test_long_messages_truncated(
    patient: Patient, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[str] = []

    def fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen.append(str(messages[-1].parts[-1].content))  # type: ignore[union-attr]
        return ModelResponse(parts=[TextPart("ok")])

    monkeypatch.setattr(handler, "get_model", lambda: FunctionModel(fn))
    monkeypatch.setattr(get_settings(), "max_message_chars", 10)
    await handler.handle(Inbound(jid=patient.whatsapp_jid, text="x" * 500))
    assert seen[0] == "x" * 10 + " […]"


def test_admin_exposure_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    from medixio.main import check_admin_exposure

    settings = get_settings()
    monkeypatch.setattr(settings, "api_host", "0.0.0.0")
    monkeypatch.setattr(settings, "admin_token", "change-me")
    with pytest.raises(SystemExit):
        check_admin_exposure()
    monkeypatch.setattr(settings, "admin_token", "a" * 32)
    check_admin_exposure()
    monkeypatch.setattr(settings, "api_host", "127.0.0.1")
    monkeypatch.setattr(settings, "admin_token", None)
    check_admin_exposure()
