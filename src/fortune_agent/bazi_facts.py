"""Explicit stem relationships and hidden stems, without strength judgments."""

from __future__ import annotations

from .bazi import BaziChart

STEMS = "甲乙丙丁戊己庚辛壬癸"
ELEMENTS = ("木", "火", "土", "金", "水")
HIDDEN_STEMS = {
    "子": ("癸",), "丑": ("己", "癸", "辛"), "寅": ("甲", "丙", "戊"),
    "卯": ("乙",), "辰": ("戊", "乙", "癸"), "巳": ("丙", "庚", "戊"),
    "午": ("丁", "己"), "未": ("己", "丁", "乙"), "申": ("庚", "壬", "戊"),
    "酉": ("辛",), "戌": ("戊", "辛", "丁"), "亥": ("壬", "甲"),
}


def ten_god(day_master: str, other: str) -> str:
    if day_master not in STEMS or len(day_master) != 1 or other not in STEMS or len(other) != 1:
        raise ValueError("十神计算需要两个有效天干")
    master_index, other_index = STEMS.index(day_master), STEMS.index(other)
    master_element, other_element = master_index // 2, other_index // 2
    same_polarity = master_index % 2 == other_index % 2
    relation = (other_element - master_element) % 5
    pairs = {
        0: ("比肩", "劫财"),
        1: ("食神", "伤官"),
        2: ("偏财", "正财"),
        3: ("七杀", "正官"),
        4: ("偏印", "正印"),
    }
    return pairs[relation][0 if same_polarity else 1]


def stem_facts(stem: str, day_master: str) -> dict[str, str]:
    if len(stem) != 1 or stem not in STEMS:
        raise ValueError("无效天干")
    index = STEMS.index(stem)
    return {
        "stem": stem,
        "element": ELEMENTS[index // 2],
        "polarity": "阳" if index % 2 == 0 else "阴",
        "ten_god": ten_god(day_master, stem),
    }


def chart_facts(chart: BaziChart) -> dict:
    result = []
    for position, pillar in zip(("年柱", "月柱", "日柱", "时柱"),
                               (chart.year, chart.month, chart.day, chart.hour), strict=True):
        if len(pillar) != 2 or pillar[1] not in HIDDEN_STEMS:
            raise ValueError("四柱中有无效干支")
        heavenly_stem = stem_facts(pillar[0], chart.day_master)
        if position == "日柱":
            heavenly_stem["role"] = "日主"
        result.append({
            "position": position,
            "ganzhi": pillar,
            "heavenly_stem": heavenly_stem,
            "branch": pillar[1],
            "hidden_stems": [stem_facts(stem, chart.day_master) for stem in HIDDEN_STEMS[pillar[1]]],
        })
    return {
        "pillars": result,
        "month_branch": chart.month[1],
        "method": "十神按日主与目标天干的五行生克及阴阳关系计算；藏干表与 lunar-python 1.4.8 对齐",
        "limitations": "藏干顺序不表示权重；未计算人元司令分日、日主强弱、格局、用神或大运",
    }
