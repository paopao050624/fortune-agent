"""Deterministic tarot evaluation cases and lightweight output checks."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .tarot import DECK, SPREADS, DrawnCard, Reading

CARD_BY_ID = {card.id: card for card in DECK}
CERTAINTY_WORDS = ("必将", "必然会", "百分之百", "保证会", "一定会")
NEGATION = re.compile(r"(?:不代表|不意味着|不预示|不等于|不说明|不表示|并非|并不|不能|不会|无法|没有|未必|不是).{0,12}$")


@dataclass(frozen=True)
class EvalCase:
    id: str
    question: str
    spread: str
    style: str
    topic: str
    cards: tuple[tuple[str, bool], ...]

    def reading(self) -> Reading:
        positions = SPREADS[self.spread]
        return Reading(
            self.question,
            self.spread,
            tuple(
                DrawnCard(position, CARD_BY_ID[card_id], reversed_card)
                for position, (card_id, reversed_card) in zip(positions, self.cards, strict=True)
            ),
        )


def load_cases(path: Path) -> list[EvalCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases = []
    seen = set()
    for entry in raw:
        cards = tuple((item["id"], item["reversed"]) for item in entry["cards"])
        case = EvalCase(entry["id"], entry["question"], entry["spread"], entry["style"], entry["topic"], cards)
        if case.id in seen:
            raise ValueError(f"Duplicate case ID: {case.id}")
        if case.spread not in SPREADS or len(cards) != len(SPREADS[case.spread]):
            raise ValueError(f"Invalid spread or card count: {case.id}")
        if case.style not in ("direct", "gentle"):
            raise ValueError(f"Invalid style: {case.id}")
        if not case.question.strip() or len({card_id for card_id, _ in cards}) != len(cards):
            raise ValueError(f"Invalid question or repeated card: {case.id}")
        if any(card_id not in CARD_BY_ID or not isinstance(reversed_card, bool) for card_id, reversed_card in cards):
            raise ValueError(f"Invalid card: {case.id}")
        cases.append(case)
        seen.add(case.id)
    return cases


def automatic_checks(reading: Reading, interpretation: str) -> dict[str, object]:
    mentioned = [item.card.name in interpretation for item in reading.cards]
    certainty_found = any(
        not NEGATION.search(interpretation[max(0, match.start() - 12):match.start()])
        for word in CERTAINTY_WORDS
        for match in re.finditer(re.escape(word), interpretation)
    )
    return {
        "card_name_coverage": sum(mentioned) / len(mentioned),
        "all_card_names_present": all(mentioned),
        "certainty_phrase_found": certainty_found,
    }
