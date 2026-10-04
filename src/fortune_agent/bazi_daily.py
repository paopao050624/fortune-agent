"""Civil-day context and ten-god relationships, without luck predictions."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

from .bazi import BaziChart, calculate_bazi
from .bazi_facts import HIDDEN_STEMS, stem_facts


def daily_bazi_context(chart: BaziChart, day: date | None = None) -> dict:
    selected=day if day is not None else datetime.now(ZoneInfo("Asia/Shanghai")).date()
    if type(selected) is not date:
        raise ValueError("每日八字参考日期必须为公历日期")
    # A single reference instant avoids pretending a solar-term month is
    # constant over an entire boundary day. No time pillar is returned.
    instant=f"{selected.isoformat()}T12:00:00+08:00"
    calendar=calculate_bazi(instant)
    pillars=[]
    for label,ganzhi in (("参考年柱",calendar.year),("参考月柱",calendar.month),("当日干支",calendar.day)):
        pillars.append({"position":label,"ganzhi":ganzhi,
                        "heavenly_stem":stem_facts(ganzhi[0],chart.day_master),
                        "hidden_stems":[stem_facts(stem,chart.day_master) for stem in HIDDEN_STEMS[ganzhi[1]]]})
    return {"date":selected.isoformat(),"timezone":"Asia/Shanghai","reference_time":instant,
            "natal_day_master":chart.day_master,"pillars":pillars,
            "previous_jie":calendar.previous_jie,"previous_jie_time":calendar.previous_jie_time,
            "next_jie":calendar.next_jie,"next_jie_time":calendar.next_jie_time,
            "calculator":calendar.calculator,
            "method":"按中国标准时间当日12:00计算参考年月与日干支；十神关系以本命日主为基准，不生成时柱。",
            "limitations":"节气切换日的上午或晚上可能与12:00参考月柱不同；仅描述干支关系，未计算大运、旺衰、合冲刑害权重或喜用神，不能确定当日吉凶。"}
