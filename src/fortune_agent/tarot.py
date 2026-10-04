"""Tarot deck and drawing rules. No interpretation or model calls live here."""

from __future__ import annotations

from dataclasses import dataclass
from random import SystemRandom
from typing import Protocol


class RandomSource(Protocol):
    def shuffle(self, x: list[Card]) -> None: ...

    def randrange(self, stop: int) -> int: ...


@dataclass(frozen=True)
class Card:
    id: str
    name: str
    suit: str | None = None


@dataclass(frozen=True)
class DrawnCard:
    position: str
    card: Card
    reversed: bool


@dataclass(frozen=True)
class Reading:
    question: str
    spread: str
    cards: tuple[DrawnCard, ...]


MAJOR_NAMES = (
    "愚者", "魔术师", "女祭司", "皇后", "皇帝", "教皇", "恋人", "战车",
    "力量", "隐者", "命运之轮", "正义", "倒吊人", "死神", "节制", "恶魔",
    "高塔", "星星", "月亮", "太阳", "审判", "世界",
)
SUITS = ("权杖", "圣杯", "宝剑", "星币")
RANKS = (
    "王牌", "二", "三", "四", "五", "六", "七", "八", "九", "十",
    "侍从", "骑士", "王后", "国王",
)
DECK = tuple(
    [Card(f"major-{number:02d}", name) for number, name in enumerate(MAJOR_NAMES)]
    + [
        Card(f"{suit_index}-{rank_index:02d}", f"{suit}{rank}", suit)
        for suit_index, suit in enumerate(SUITS, start=1)
        for rank_index, rank in enumerate(RANKS, start=1)
    ]
)
SPREADS = {
    "single": ("今日提示",),
    "three": ("现状", "影响", "建议"),
}


def draw_reading(
    question: str,
    spread: str = "single",
    selected_positions: tuple[int, ...] | None = None,
    rng: RandomSource | None = None,
) -> Reading:
    """Shuffle once, then reveal user-selected slots or draw from the top.

    Positions are one-based indexes in the shuffled 78-card deck. An injected
    random source allows deterministic tests; normal use uses OS randomness.
    """
    if spread not in SPREADS:
        raise ValueError(f"Unknown spread: {spread}")
    if not question.strip():
        raise ValueError("Question cannot be empty")

    positions = SPREADS[spread]
    if selected_positions is not None:
        if len(selected_positions) != len(positions):
            raise ValueError(f"{spread} requires {len(positions)} selected positions")
        if len(set(selected_positions)) != len(selected_positions):
            raise ValueError("Selected positions must be distinct")
        if any(not 1 <= index <= len(DECK) for index in selected_positions):
            raise ValueError("Selected positions must be between 1 and 78")

    source: RandomSource = rng if rng is not None else SystemRandom()
    shuffled = list(DECK)
    source.shuffle(shuffled)
    indexes = selected_positions or tuple(range(1, len(positions) + 1))
    cards = tuple(
        DrawnCard(position, shuffled[index - 1], bool(source.randrange(2)))
        for position, index in zip(positions, indexes, strict=True)
    )
    return Reading(question.strip(), spread, cards)
