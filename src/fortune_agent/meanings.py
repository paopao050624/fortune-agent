"""Source-traced tarot meanings supplied to the interpretation model."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files

from .tarot import Reading


@lru_cache(maxsize=1)
def load_catalog() -> dict:
    resource = files("fortune_agent").joinpath("data/waite_meanings.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def evidence_for(reading: Reading) -> tuple[dict[str, object], ...]:
    catalog = load_catalog()
    evidence = []
    for item in reading.cards:
        entry = catalog["cards"].get(item.card.id)
        orientation = "reversed" if item.reversed else "upright"
        meaning = entry.get(orientation) if entry else None
        if meaning:
            evidence.append({
                "card_id": item.card.id,
                "orientation": orientation,
                "status": "sourced",
                "source_id": catalog["source"]["id"],
                "source_text": meaning,
                "source_url": entry["source_url"],
            })
        else:
            evidence.append({
                "card_id": item.card.id,
                "orientation": orientation,
                "status": "unavailable",
                "source_id": None,
                "source_text": None,
                "source_url": None,
            })
    return tuple(evidence)
