"""Image -> structured data, in memory only. Images are never stored (design §6.1)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent, BinaryContent, ToolOutput


class ExtractedItem(BaseModel):
    medicine_name: str
    presentation: str | None = None
    dose_text: str | None = Field(None, description="Literal, tal como aparece")
    quantity_per_dispense: str | None = None


class DocumentExtraction(BaseModel):
    kind: Literal["order", "authorization", "appointment", "other"]
    confidence: Literal["high", "medium", "low"]
    doctor_name: str | None = None
    specialty: str | None = None
    issued_on: date | None = None
    duration_months: int | None = Field(
        None, description="Duración del tratamiento de la fórmula, en meses"
    )
    items: list[ExtractedItem] = []
    authorization_number: str | None = None
    service_description: str | None = None
    valid_until: date | None = None
    eps: str | None = None
    provider: str | None = Field(None, description="Farmacia o IPS donde se presta")
    appointment_at: datetime | None = Field(None, description="Hora local de Colombia")
    location: str | None = None
    unreadable_fields: list[str] = []
    summary: str = Field(description="Resumen corto en español de lo que dice")


extractor = Agent(
    # strict=False: Anthropic rejects this schema as "too complex" in strict mode
    output_type=ToolOutput(DocumentExtraction, strict=False),
    instructions=(
        "Extrae datos de una foto de un documento médico-administrativo colombiano: "
        "fórmula/orden médica, autorización de EPS o soporte de cita. "
        "Copia los textos literalmente; no interpretes dosis. "
        "Si un dato no se lee con claridad, déjalo vacío y añádelo a "
        "unreadable_fields. "
        "authorization_number es solo el número de autorización de la EPS; no uses "
        "ahí números de comprobante, consecutivo, cita, factura ni radicado. "
        "Fechas en formato colombiano día/mes/año."
    ),
)


async def extract(
    image: bytes, media_type: str, caption: str | None
) -> DocumentExtraction:
    from medixio.agent.model import get_model

    prompt: list[str | BinaryContent] = [
        BinaryContent(data=image, media_type=media_type)
    ]
    if caption:
        prompt.append(f"Texto del usuario: {caption}")
    from medixio.observability import obs

    result = await extractor.run(prompt, model=get_model())
    obs().metric("agent.tokens_in", result.usage.input_tokens or 0, source="extraction")
    obs().metric(
        "agent.tokens_out", result.usage.output_tokens or 0, source="extraction"
    )
    return result.output
