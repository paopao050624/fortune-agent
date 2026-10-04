"""A reproducible one-card reading for each profile's local calendar day."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .tarot import DECK, DrawnCard, Reading

ALGORITHM = "daily-tarot-v1"


@dataclass(frozen=True)
class DailyDraw:
    day: str
    timezone: str
    cache_key: str
    reading: Reading


def daily_draw(profile_id: str, timezone_name: str, at: datetime | None = None) -> DailyDraw:
    profile = profile_id.strip()
    if not profile or len(profile) > 128:
        raise ValueError("用户代号必须为 1–128 个字符")
    if not timezone_name.strip():
        raise ValueError("请提供 IANA 时区，例如 Asia/Shanghai")
    try:
        local_zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"无效的时区：{timezone_name}") from exc

    instant = at if at is not None else datetime.now(timezone.utc)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("指定时间必须包含时区")
    day = instant.astimezone(local_zone).date().isoformat()

    material = json.dumps(
        [ALGORITHM, profile, timezone_name, day], ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    digest = hashlib.sha256(material).digest()
    index = int.from_bytes(digest[:16], "big") % len(DECK)
    reversed_card = bool(digest[16] & 1)
    reading = Reading(
        question=f"{day}（{timezone_name}）的每日塔罗提示是什么？",
        spread="single",
        cards=(DrawnCard("今日提示", DECK[index], reversed_card),),
    )
    return DailyDraw(day, timezone_name, digest.hex(), reading)
