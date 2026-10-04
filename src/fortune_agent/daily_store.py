"""Local cache for a daily reading's first model interpretation."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from .agent import AgentResult
from .daily import DailyDraw


class DailyStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(descriptor)
        self.path.chmod(0o600)
        with closing(self._connect()) as connection:
            with connection:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS daily_interpretations (
                        cache_key TEXT PRIMARY KEY,
                        card_id TEXT NOT NULL,
                        reversed INTEGER NOT NULL,
                        model TEXT NOT NULL,
                        style TEXT NOT NULL,
                        interpretation TEXT NOT NULL,
                        evidence_json TEXT NOT NULL
                    )
                """)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=10)

    def get(self, draw: DailyDraw) -> tuple[str, tuple[dict, ...], str] | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT card_id, reversed, interpretation, evidence_json, style "
                "FROM daily_interpretations WHERE cache_key = ?",
                (draw.cache_key,),
            ).fetchone()
        if row is None:
            return None
        card = draw.reading.cards[0]
        if row[0] != card.card.id or bool(row[1]) != card.reversed:
            raise RuntimeError("本地每日缓存与当前抽牌规则不一致")
        return row[2], tuple(json.loads(row[3])), row[4]

    def save(self, draw: DailyDraw, result: AgentResult, model: str, style: str) -> tuple[str, tuple[dict, ...], str]:
        if result.reading != draw.reading:
            raise ValueError("模型解读的牌面与每日抽牌结果不一致")
        card = draw.reading.cards[0]
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    "INSERT OR IGNORE INTO daily_interpretations "
                    "(cache_key, card_id, reversed, model, style, interpretation, evidence_json) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (draw.cache_key, card.card.id, int(card.reversed), model, style,
                     result.interpretation, json.dumps(result.evidence, ensure_ascii=False)),
                )
        saved = self.get(draw)
        if saved is None:
            raise RuntimeError("每日解读未能保存")
        return saved
