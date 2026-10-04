"""Daily card plus one locally cached interpretation when requested."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .agent import TarotAgent
from .daily import daily_draw
from .daily_store import DailyStore
from .tarot import Reading


@dataclass(frozen=True)
class DailyResult:
    day: str
    timezone: str
    reading: Reading
    interpretation: str | None = None
    evidence: tuple[dict[str, object], ...] = ()
    style: str | None = None
    cached: bool = False


def get_daily(
    profile_id: str,
    timezone_name: str,
    *,
    store: DailyStore | None = None,
    client: Any = None,
    model: str | None = None,
    style: str = "gentle",
    at: datetime | None = None,
) -> DailyResult:
    draw = daily_draw(profile_id, timezone_name, at)
    if store is None:
        return DailyResult(draw.day, draw.timezone, draw.reading)

    existing = store.get(draw)
    if existing is not None:
        interpretation, evidence, saved_style = existing
        return DailyResult(draw.day, draw.timezone, draw.reading, interpretation, evidence, saved_style, True)
    if client is None or not model:
        raise ValueError("首次解读需要中转站客户端和模型")

    agent = TarotAgent(client, model, draw=lambda *_: draw.reading)
    result = agent.read(draw.reading.question, style=style)
    interpretation, evidence, saved_style = store.save(draw, result, model, style)
    return DailyResult(draw.day, draw.timezone, draw.reading, interpretation, evidence, saved_style)
