"""Per-number and global limits against spam, cost abuse and WhatsApp bans.

Counters live in the observability store (sliding windows), so they survive restarts
and never touch patient data. Over a limit the bot answers once with a notice and
then stays silent until the window frees up.
"""

import logging
import time
from dataclasses import dataclass

from medixio.config import get_settings
from medixio.observability import obs


log = logging.getLogger(__name__)

TEN_MIN = 600
HOUR = 3600
DAY = 86400

MSG_NOTICE = (
    "Estás enviando muchos mensajes seguidos 🙏. Espera unos minutos y "
    "seguimos. Tus recordatorios siguen activos."
)
IMG_NOTICE = (
    "Por hoy ya recibí el máximo de fotos 📷. Mañana puedes enviarme más, o "
    "escríbeme los datos en texto."
)
BUDGET_NOTICE = (
    "Estoy recibiendo muchos mensajes en este momento 😕. Inténtalo de nuevo "
    "más tarde. Tus recordatorios siguen activos."
)


@dataclass
class Decision:
    allowed: bool
    notice: str | None = None  # reply to send when blocked; None = stay silent
    reason: str | None = None


def _count(subject: str, kind: str, window: int) -> int:
    rows = obs().query(
        "SELECT COUNT(*) AS n FROM rate_event WHERE subject = ? AND kind = ? "
        "AND ts >= ?",
        (subject, kind, time.time() - window),
    )
    return int(rows[0]["n"])


def _hit(subject: str, kind: str) -> None:
    obs().write("INSERT INTO rate_event VALUES (?, ?, ?)", (time.time(), subject, kind))


def tokens_last_day() -> int:
    rows = obs().query(
        "SELECT COALESCE(SUM(value), 0) AS n FROM metric "
        "WHERE name IN ('agent.tokens_in', 'agent.tokens_out') AND ts >= ?",
        (time.time() - DAY,),
    )
    return int(rows[0]["n"])


def _blocked(jid: str, reason: str, notice: str) -> Decision:
    obs().metric("ratelimit.blocked", 1, reason=reason)
    # One notice per number per reason every 10 minutes; silence otherwise.
    if _count(jid, f"notice:{reason}", TEN_MIN):
        return Decision(False, None, reason)
    _hit(jid, f"notice:{reason}")
    log.warning("rate limited jid=%s reason=%s", mask(jid), reason)
    return Decision(False, notice, reason)


def check_message(jid: str, *, has_image: bool) -> Decision:
    """Call once per inbound message, before any LLM work."""
    s = get_settings()
    if tokens_last_day() >= s.daily_token_budget:
        return _blocked(jid, "token_budget", BUDGET_NOTICE)
    if (
        _count(jid, "msg", TEN_MIN) >= s.rate_msgs_per_10min
        or _count(jid, "msg", DAY) >= s.rate_msgs_per_day
    ):
        return _blocked(jid, "messages", MSG_NOTICE)
    if has_image and _count(jid, "img", DAY) >= s.rate_images_per_day:
        return _blocked(jid, "images", IMG_NOTICE)
    _hit(jid, "msg")
    if has_image:
        _hit(jid, "img")
    return Decision(True)


def check_signup() -> bool:
    """Global cap on new numbers per hour. Over it, unknown numbers are ignored."""
    if _count("*", "signup", HOUR) >= get_settings().rate_signups_per_hour:
        obs().metric("ratelimit.blocked", 1, reason="signups")
        log.warning("signup rate limit reached")
        return False
    _hit("*", "signup")
    return True


def truncate(text: str) -> str:
    limit = get_settings().max_message_chars
    return text if len(text) <= limit else text[:limit] + " […]"


def mask(jid: str) -> str:
    user = jid.split("@", 1)[0]
    return f"{user[:4]}…{user[-2:]}" if len(user) > 6 else "…"


def blocked_numbers(hours: int = 24) -> list[dict[str, object]]:
    rows = obs().query(
        "SELECT subject, kind, COUNT(*) AS n, MAX(ts) AS last FROM rate_event "
        "WHERE kind LIKE 'notice:%' AND ts >= ? GROUP BY subject, kind "
        "ORDER BY last DESC",
        (time.time() - hours * HOUR,),
    )
    return [
        {
            "number": mask(r["subject"]),
            "reason": r["kind"].removeprefix("notice:"),
            "times": r["n"],
            "last": r["last"],
        }
        for r in rows
    ]
