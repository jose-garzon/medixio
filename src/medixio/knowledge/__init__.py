"""Shared bureaucracy rules with per-patient overrides (design §5)."""

import json
import re
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel
from sqlmodel import Session, select

from medixio.modules.patients.models import PatientPreference


KNOWLEDGE_DIR = Path(__file__).parent


class Rule(BaseModel):
    key: str
    value: Any
    source: str
    reviewed_on: date | None = None

    @property
    def usable(self) -> bool:
        return self.source == "product" or self.reviewed_on is not None


class Guide(BaseModel):
    topic: str
    sources: list[str]
    reviewed_on: date | None
    body: str


@lru_cache
def rules() -> dict[str, Rule]:
    raw = yaml.safe_load((KNOWLEDGE_DIR / "defaults.yaml").read_text())
    return {key: Rule(key=key, **entry) for key, entry in raw.items()}


@lru_cache
def guides() -> dict[str, Guide]:
    result = {}
    for path in sorted((KNOWLEDGE_DIR / "guides").glob("*.md")):
        match = re.match(r"^---\n(.*?)\n---\n(.*)$", path.read_text(), re.S)
        if not match:
            continue
        meta = yaml.safe_load(match.group(1))
        result[meta["topic"]] = Guide(body=match.group(2).strip(), **meta)
    return result


def resolve(session: Session, patient_id: str, key: str) -> Any | None:
    """Patient override, else the shared rule if usable, else None."""
    pref = session.exec(
        select(PatientPreference).where(
            PatientPreference.patient_id == patient_id, PatientPreference.key == key
        )
    ).first()
    if pref is not None:
        return json.loads(pref.value)
    rule = rules().get(key)
    if rule is None or not rule.usable:
        return None
    return rule.value


def unreviewed() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = [
        {"kind": "rule", "key": r.key, "source": r.source}
        for r in rules().values()
        if not r.usable
    ]
    items += [
        {"kind": "guide", "key": g.topic, "source": "; ".join(g.sources)}
        for g in guides().values()
        if g.reviewed_on is None
    ]
    return items
