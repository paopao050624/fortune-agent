"""Fixed synthetic cases and mechanical checks for four-pillar explanations."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .bazi import BaziChart, calculate_bazi

PILLAR_PATTERN = re.compile(r"[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]")
CLASSIC_TITLES = ("渊海子平", "三命通会", "子平真诠", "滴天髓", "穷通宝鉴")


@dataclass(frozen=True)
class BaziCase:
    id: str
    birth: str
    question: str
    topic: str

    def chart(self) -> BaziChart:
        return calculate_bazi(self.birth)


def load_cases(path: Path) -> list[BaziCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases = [BaziCase(**item) for item in raw]
    if len({case.id for case in cases}) != len(cases):
        raise ValueError("八字评估案例 ID 重复")
    if any(not case.id or not case.question.strip() for case in cases):
        raise ValueError("八字评估案例缺少 ID 或问题")
    return cases


def automatic_checks(chart: BaziChart, answer: str) -> dict[str, object]:
    expected = [chart.year, chart.month, chart.day, chart.hour]
    mentioned = [pillar in answer for pillar in expected]
    found = set(PILLAR_PATTERN.findall(answer))
    unexpected = sorted(found - set(expected))
    return {
        "pillar_mentions": sum(mentioned),
        "pillar_count": 4,
        "unexpected_pillars": unexpected,
        "day_master_mentioned": chart.day_master in answer,
        "true_solar_time_limit_mentioned": "真太阳时" in answer,
        "classic_titles_mentioned": [title for title in CLASSIC_TITLES if title in answer],
    }
