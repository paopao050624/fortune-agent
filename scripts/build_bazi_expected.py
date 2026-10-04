"""Regenerate checked-in four-pillar fixtures from the pinned calculator."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from fortune_agent.bazi_evaluation import load_cases

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evals/bazi_cases.json"
OUTPUT = ROOT / "evals/bazi_expected.json"


def main() -> None:
    records = [
        {"case_id": case.id, "chart": asdict(case.chart())}
        for case in load_cases(SOURCE)
    ]
    OUTPUT.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(records)} charts to {OUTPUT}")


if __name__ == "__main__":
    main()
