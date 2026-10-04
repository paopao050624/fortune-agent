"""Show source conditions and observed stems without inferring a pattern."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files

from .bazi import BaziChart
from .bazi_facts import chart_facts

GROUPS = {
    "wealth_visible": ("财星透干", ("正财", "偏财")),
    "official_visible": ("正官透干", ("正官",)),
    "food_god_visible": ("食神透干", ("食神",)),
    "peer_visible": ("比肩或劫财天干可见", ("比肩", "劫财")),
    "resource_visible": ("印星透干（正印或偏印）", ("正印", "偏印")),
}

# These anchors are transcribed from the inspected page. They verify that the
# curated checklist remains attached to the same wording, not its truthfulness.
SOURCE_ANCHORS = {
    "wealth-generates-official": "財旺生官",
    "output-generates-wealth": "財逢食生而身強帶比",
    "wealth-with-resource": "財格透印而位置妥適，兩不相剋",
}
REQUIRED_UNKNOWN = {
    "wealth-generates-official": {"命局已确认为财格", "财旺", "财生官的有效配合"},
    "output-generates-wealth": {"命局已确认为财格", "财逢食生的有效配合", "身强", "原文带比条件是否满足"},
    "wealth-with-resource": {"命局已确认为财格", "所见印星是否符合此路径取用条件", "位置妥适", "两不相克"},
}


def validate_rule_catalog(catalog: dict, source_entries: list[dict]) -> None:
    matches = [entry for entry in source_entries if entry["id"] == catalog["source_id"]]
    if len(matches) != 1:
        raise ValueError("财格清单未对应到唯一来源")
    source = matches[0]
    if source["chapter"] != "论用神成败救应" or source["scan_pages"] != [28] or source["printed_pages"] != [19]:
        raise ValueError("财格清单来源章节或页码与核对记录不一致")
    paths = catalog["paths"]
    if len(paths) != 3 or {path["id"] for path in paths} != set(SOURCE_ANCHORS):
        raise ValueError("财格清单须保留三条唯一方法路径")
    for path in paths:
        path_id = path["id"]
        if SOURCE_ANCHORS[path_id] not in source["source_text"]:
            raise ValueError(f"财格路径原文不匹配：{path_id}")
        groups = path["observation_groups"]
        if not groups or len(groups) != len(set(groups)) or not set(groups) <= set(GROUPS):
            raise ValueError(f"财格路径观察字段无效：{path_id}")
        if not REQUIRED_UNKNOWN[path_id] <= set(path["unverified_conditions"]):
            raise ValueError(f"财格路径缺少待核实条件：{path_id}")


@lru_cache(maxsize=1)
def load_rule_catalog() -> dict:
    resources = files("fortune_agent")
    catalog = json.loads(resources.joinpath("data/bazi_wealth_rules.json").read_text(encoding="utf-8"))
    sources = json.loads(resources.joinpath("data/ziping_sources.json").read_text(encoding="utf-8"))
    validate_rule_catalog(catalog, sources["entries"])
    return catalog


def wealth_checklist(chart: BaziChart) -> dict:
    facts = chart_facts(chart)
    visible = [pillar for pillar in facts["pillars"] if pillar["position"] != "日柱"]
    observations = {}
    for key, (label, gods) in GROUPS.items():
        matches = [{"position": pillar["position"], **pillar["heavenly_stem"]}
                   for pillar in visible if pillar["heavenly_stem"]["ten_god"] in gods]
        observations[key] = {"label": label, "present": bool(matches), "stems": matches}
    month_pillar = facts["pillars"][1]
    month_wealth = [item for item in month_pillar["hidden_stems"] if item["ten_god"] in ("正财", "偏财")]
    catalog = load_rule_catalog()
    paths = [{
        "id": path["id"], "label": path["label"],
        "observations": [observations[key] for key in path["observation_groups"]],
        "unverified_conditions": path["unverified_conditions"],
        "status": "unverified",
    } for path in catalog["paths"]]
    return {
        "method_version": catalog["version"],
        "source_id": catalog["source_id"],
        "month_branch": facts["month_branch"],
        "month_wealth_hidden_stems": month_wealth,
        "observations": observations,
        "paths": paths,
        "conclusion": "undetermined",
        "limitations": "财格方法学习清单，不是定格结果；未见透干不等于该星不存在，藏干不参与透干观察。",
    }
