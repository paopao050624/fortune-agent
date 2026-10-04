"""Retrieve a verified transcription excerpt by the computed day stem."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from importlib.resources import files

from .bazi import BaziChart
from .bazi_rules import load_rule_catalog


@lru_cache(maxsize=1)
def load_catalog() -> dict:
    resource = files("fortune_agent").joinpath("data/bazi_sources.json")
    return json.loads(resource.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_context_catalog() -> dict:
    resource = files("fortune_agent").joinpath("data/bazi_context_sources.json")
    return json.loads(resource.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_ziping_catalog() -> dict:
    resource = files("fortune_agent").joinpath("data/ziping_sources.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def catalog_sha256() -> str:
    content = json.dumps({"stems": load_catalog(), "context": load_context_catalog(),
                          "ziping": load_ziping_catalog(), "wealth_rules": load_rule_catalog()},
                         ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def evidence_for(chart: BaziChart) -> tuple[dict, ...]:
    catalog = load_catalog()
    matched = [entry for entry in catalog["entries"] if entry["stem"] == chart.day_master]
    if len(matched) != 1:
        raise ValueError("日主未对应到唯一的古籍条目")
    stem_evidence = {
        **matched[0],
        "edition_note": catalog["source"]["edition_note"],
        "retrieval_basis": "程序计算的日主；仅检索该天干的历史原文，不构成整体命局判断",
    }
    ziping = load_ziping_catalog()
    ziping_evidence = tuple({
        **entry,
        "edition_note": ziping["source"]["edition_note"],
        "punctuation_policy": ziping["source"]["punctuation_policy"],
        "scan_sha256": ziping["source"]["file_sha256"],
    } for entry in ziping["entries"])
    return (stem_evidence, *load_context_catalog()["entries"], *ziping_evidence)
