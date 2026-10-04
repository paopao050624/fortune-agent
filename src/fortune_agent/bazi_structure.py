"""Traceable structural observations and pattern-study candidates."""
from functools import lru_cache
from importlib.resources import files
import json

from .bazi import BaziChart
from .bazi_facts import ELEMENTS, HIDDEN_STEMS, chart_facts, stem_facts


@lru_cache(maxsize=1)
def load_structure_rules():
    rules=json.loads(files("fortune_agent").joinpath("data/bazi_structure_rules.json").read_text(encoding="utf-8"))
    if set(rules["season_groups"])!=set(HIDDEN_STEMS):
        raise ValueError("结构规则的月支分类不完整")
    if set(rules["pattern_labels"])!={"正官","七杀","正财","偏财","正印","偏印","食神","伤官"}:
        raise ValueError("结构规则的普通格局候选分类不完整")
    if not rules["unresolved"] or not rules["source_ids"]:
        raise ValueError("结构规则缺少来源或未核实条件")
    sources=json.loads(files("fortune_agent").joinpath("data/ziping_sources.json").read_text(encoding="utf-8"))["entries"]
    lookup={entry["id"]:entry for entry in sources}
    if not set(rules["source_ids"])<=set(lookup):
        raise ValueError("结构规则包含未提供的来源")
    if lookup["ziping-root-observation"]["scan_pages"]!=[22] or lookup["ziping-root-observation"]["printed_pages"]!=[13]:
        raise ValueError("通根来源页码与核对记录不一致")
    return rules


def analyze_structure(chart: BaziChart) -> dict:
    if chart.day_master!=chart.day[0]:
        raise ValueError("日主必须与日柱天干一致")
    facts=chart_facts(chart)
    rules=load_structure_rules()
    visible=[p for p in facts["pillars"] if p["position"]!="日柱"]
    master_element=stem_facts(chart.day_master,chart.day_master)["element"]
    season=rules["season_groups"][facts["month_branch"]]
    dominant=rules["season_elements"].get(season)
    season_relation=None
    if dominant:
        # This is a five-element relation, not a hidden-stem weight or strength score.
        relation=(ELEMENTS.index(dominant)-ELEMENTS.index(master_element))%5
        season_relation=("同类","日主生季节五行","日主克季节五行","季节五行克日主","季节五行生日主")[relation]
    roots=[]
    for pillar in facts["pillars"]:
        stem=pillar["heavenly_stem"]
        locations=[]
        for other in facts["pillars"]:
            for hidden in other["hidden_stems"]:
                if hidden["element"]==stem["element"]:
                    locations.append({"position":other["position"],"branch":other["branch"],
                                      "hidden_stem":hidden["stem"],
                                      "match":"same_stem" if hidden["stem"]==stem["stem"] else "same_element"})
        roots.append({"position":pillar["position"],"stem":stem["stem"],"element":stem["element"],
                      "is_day_master":pillar["position"]=="日柱","locations":locations,
                      "observation":"同类藏干出现" if locations else "四支未见同五行藏干",
                      "root_strength":"unassessed"})

    month_hidden=facts["pillars"][1]["hidden_stems"]
    transmission=[]
    candidates=[]
    special=[]
    for hidden in month_hidden:
        positions=[p["position"] for p in visible if p["heavenly_stem"]["stem"]==hidden["stem"]]
        entry={**hidden,"visible_positions":positions,"transmitted":bool(positions)}
        transmission.append(entry)
        if hidden["ten_god"] in ("比肩","劫财"):
            special.append({"stem":hidden["stem"],"ten_god":hidden["ten_god"],
                            "reason":"月令含同类，应另查建禄、月劫、阳刃等条件；此版本未按十神标签自动定格。"})
            continue
        candidates.append({"id":"month-hidden-"+hidden["stem"],"label":rules["pattern_labels"][hidden["ten_god"]],
                           "month_branch":facts["month_branch"],"stem":hidden["stem"],"ten_god":hidden["ten_god"],
                           "transmitted":bool(positions),"visible_positions":positions,"status":"candidate_only",
                           "source_ids":["ziping-yongshen-month-origin","ziping-yongshen-pillar-coordination"],
                           "conditions_to_check":["月令取用的实际适用条件","多藏干与透干的取舍","整体旺衰","其他干支的成败救应"]})
    trace=[
        {"rule":"month-season","description":"按节气月支作季节标签；季末月不直接判土旺或得令", "source_ids":["ziping-season-not-final"]},
        {"rule":"root-observation","description":"逐柱列出同干与同五行藏干位置，不给根力分数", "source_ids":["ziping-root-observation"]},
        {"rule":"month-transmission","description":"月支藏干与非日干逐字比对，记录透出位置", "source_ids":["ziping-yongshen-pillar-coordination"]},
        {"rule":"pattern-study-candidates","description":"按月支藏干十神给出研究候选，不排名、不宣称成格", "source_ids":["ziping-yongshen-month-origin","ziping-yongshen-pillar-coordination"]},
    ]
    return {"method_version":rules["version"],"day_master":chart.day_master,
            "season":{"month_branch":facts["month_branch"],"label":season,"associated_element":dominant,
                      "relation_to_day_master":season_relation,"strength_status":"unassessed"},
            "roots":roots,"month_transmission":transmission,"pattern_candidates":candidates,
            "special_case_flags":special,"trace":trace,"unresolved":rules["unresolved"],
            "strength_conclusion":"undetermined","pattern_conclusion":"undetermined","useful_god_conclusion":"undetermined",
            "limitations":"程序已计算关系与候选，尚未判定根力、整体旺衰、最终格局、喜用神或大运；列表顺序不是优先级。"}
