"""Four-pillar calculation with an explicit first-version convention."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class BaziChart:
    birth_time: str
    timezone: str
    year: str
    month: str
    day: str
    hour: str
    day_master: str
    previous_jie: str
    previous_jie_time: str
    next_jie: str
    next_jie_time: str
    day_boundary_rule: str
    solar_time_rule: str
    calculator: str


def calculate_bazi(birth_time: str, timezone_name: str = "Asia/Shanghai") -> BaziChart:
    """Calculate using China standard time and lunar-python's sect 2 day rule.

    Version 1 accepts only Asia/Shanghai civil time. The library computes solar
    terms for that clock; other zones need an explicit conversion policy first.
    """
    if timezone_name != "Asia/Shanghai":
        raise ValueError("当前八字排盘仅支持 Asia/Shanghai 时区")
    try:
        birth = datetime.fromisoformat(birth_time)
    except ValueError as exc:
        raise ValueError("出生时间应为 ISO 8601 格式，例如 2000-01-01T12:00:00+08:00") from exc
    if birth.tzinfo is None or birth.utcoffset() is None:
        raise ValueError("出生时间必须包含 +08:00 时区偏移")
    zone = ZoneInfo("Asia/Shanghai")
    local = birth.astimezone(zone)
    if local.utcoffset() != birth.utcoffset() or birth.utcoffset().total_seconds() != 8 * 3600:
        raise ValueError("出生时间必须使用 Asia/Shanghai 的 +08:00 法定时间")
    if not 1900 <= local.year <= 2100:
        raise ValueError("当前排盘支持 1900–2100 年出生时间")

    try:
        from lunar_python import Solar
    except ImportError as exc:
        raise RuntimeError("请安装八字可选依赖：pip install -e '.[bazi]'") from exc

    solar = Solar.fromYmdHms(local.year, local.month, local.day,
                             local.hour, local.minute, local.second)
    lunar = solar.getLunar()
    pillars = lunar.getEightChar()
    pillars.setSect(2)
    prev_jie = lunar.getPrevJie()
    next_jie = lunar.getNextJie()
    return BaziChart(
        birth_time=local.isoformat(timespec="seconds"),
        timezone=timezone_name,
        year=pillars.getYear(),
        month=pillars.getMonth(),
        day=pillars.getDay(),
        hour=pillars.getTime(),
        day_master=pillars.getDayGan(),
        previous_jie=prev_jie.getName(),
        previous_jie_time=prev_jie.getSolar().toYmdHms(),
        next_jie=next_jie.getName(),
        next_jie_time=next_jie.getSolar().toYmdHms(),
        day_boundary_rule="sect-2: 23:00 后日柱仍按当日，00:00 换日",
        solar_time_rule="法定时间；未做真太阳时校正",
        calculator="lunar-python 1.4.8",
    )
