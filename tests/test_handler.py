import os
from pathlib import Path

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from sqlmodel import Session, select

from medixio import handler
from medixio.channel.base import Inbound
from medixio.extraction import DocumentExtraction, ExtractedItem
from medixio.modules.conversations.models import Message
from medixio.modules.orders.models import MedicalOrder
from medixio.modules.patients.models import Patient


JID = "573009998877@s.whatsapp.net"


def _text_model(reply: str) -> FunctionModel:
    def fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart(reply)])

    return FunctionModel(fn)


@pytest.mark.asyncio
async def test_consent_gate(monkeypatch: pytest.MonkeyPatch, session: Session) -> None:
    monkeypatch.setattr(handler, "get_model", lambda: _text_model("hola"))
    first = await handler.handle(Inbound(jid=JID, text="hola"))
    assert first == handler.CONSENT_TEXT
    again = await handler.handle(Inbound(jid=JID, text="qué es esto"))
    assert again == handler.CONSENT_TEXT
    ok = await handler.handle(Inbound(jid=JID, text="Acepto"))
    assert ok == handler.CONSENT_OK
    reply = await handler.handle(Inbound(jid=JID, text="Ana"))
    assert reply == "hola"
    assert len(session.exec(select(Message)).all()) == 3


@pytest.mark.asyncio
async def test_image_order_saved_only_after_confirmation(
    monkeypatch: pytest.MonkeyPatch, session: Session, patient: Patient, tmp_path: Path
) -> None:
    async def fake_extract(image: bytes, media_type: str, caption: str | None):  # type: ignore[no-untyped-def]
        return DocumentExtraction(
            kind="order",
            confidence="high",
            issued_on="2026-10-30",  # type: ignore[arg-type]
            duration_months=3,
            items=[ExtractedItem(medicine_name="Losartán 50 mg")],
            summary="Fórmula por 3 meses",
        )

    calls = {"n": 0}

    def fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        calls["n"] += 1
        last = messages[-1].parts[-1]
        if getattr(last, "part_kind", "") == "tool-return":
            return ModelResponse(parts=[TextPart("Listo, guardada ✅")])
        content = str(getattr(last, "content", ""))
        if content.strip().lower() == "sí":
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "create_order",
                        {
                            "issued_on": "2026-10-30",
                            "duration_months": 3,
                            "items": [{"medicine_name": "Losartán 50 mg"}],
                            "extracted_from_image": True,
                        },
                    )
                ]
            )
        return ModelResponse(
            parts=[TextPart("Leí Losartán 50 mg por 3 meses. ¿Está bien así?")]
        )

    monkeypatch.setattr(handler, "extract", fake_extract)
    monkeypatch.setattr(handler, "get_model", lambda: FunctionModel(fn))
    monkeypatch.chdir(tmp_path)

    jid = patient.whatsapp_jid
    reply = await handler.handle(
        Inbound(jid=jid, text="", image=b"\xff\xd8fake", image_media_type="image/jpeg")
    )
    assert "¿Está bien así?" in (reply or "")
    assert session.exec(select(MedicalOrder)).all() == []
    assert os.listdir(tmp_path) == []  # nothing written to disk

    reply = await handler.handle(Inbound(jid=jid, text="sí"))
    assert reply == "Listo, guardada ✅"
    session.expire_all()
    (order,) = session.exec(select(MedicalOrder)).all()
    assert order.extracted_from_image
    stored = [m.content for m in session.exec(select(Message)).all()]
    assert any("[imagen recibida: order" in c for c in stored)


@pytest.mark.asyncio
async def test_delete_my_data(
    monkeypatch: pytest.MonkeyPatch, session: Session, patient: Patient
) -> None:
    def fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        last = messages[-1].parts[-1]
        if getattr(last, "part_kind", "") == "tool-return":
            return ModelResponse(parts=[TextPart("chao")])
        return ModelResponse(
            parts=[
                ToolCallPart(
                    "request_data_deletion", {"confirmation_phrase": "BORRAR MIS DATOS"}
                )
            ]
        )

    monkeypatch.setattr(handler, "get_model", lambda: FunctionModel(fn))
    reply = await handler.handle(
        Inbound(jid=patient.whatsapp_jid, text="BORRAR MIS DATOS")
    )
    assert reply == handler.DELETED_TEXT
    session.expire_all()
    assert session.exec(select(Patient)).all() == []
