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
    special = rules["special_months"]
    if set(special["lu"]) != set("甲乙丙丁戊己庚辛壬癸") or set(special["yang_blade"]) != set("甲丙戊庚壬"):
        raise ValueError("禄刃映射的适用范围不完整")
    if set(special["yin_month_jie"]) != set("乙丁己辛癸"):
        raise ValueError("阴干月劫映射的适用范围不完整")
    if lookup["ziping-root-observation"]["scan_pages"]!=[22] or lookup["ziping-root-observation"]["printed_pages"]!=[13]:
        raise ValueError("通根来源页码与核对记录不一致")
    return rules


def select_research_paths(facts: dict, candidates: list, rules: dict) -> dict:
    """Select evidence to investigate, without declaring formation or transformation."""
    master = facts["pillars"][2]["heavenly_stem"]["stem"]
    month = facts["month_branch"]
    maps = rules["special_months"]
    route = "ordinary"
    label = "普通月令研究"
    source_ids = ["ziping-yongshen-month-origin"]
    if maps["lu"].get(master) == month:
        route, label = "jian_lu", "建禄月研究路径"
        source_ids = ["ziping-lu-jie-method"]
    elif maps["yang_blade"].get(master) == month:
        route, label = "yang_blade", "阳刃月研究路径（五阳干约定）"
        source_ids = ["ziping-yang-blade"]
    elif maps["yin_month_jie"].get(master) == month:
        route, label = "month_jie", "阴干月劫研究路径"
        source_ids = ["ziping-lu-jie-method"]
    elif month in "辰戌丑未":
        route, label = "mixed_qi", "杂气月研究路径"
        source_ids = ["ziping-mixed-selection", "ziping-mixed-conflict"]

    combinations = []
    present = {p["branch"] for p in facts["pillars"]}
    for group in rules["three_combinations"]:
        required = set(group["branches"])
        if month in required and required <= present:
            combinations.append({
                **group,
                "positions": [{"position": p["position"], "branch": p["branch"]}
                              for p in facts["pillars"] if p["branch"] in required],
                "status": "branch_set_only",
                "transformation": "unassessed",
            })

    selection = []
    for candidate in candidates:
        stem = stem_facts(candidate["stem"], master)
        support = []
        if candidate["transmitted"]:
            support.append("exact_transmission")
        if any(group["element"] == stem["element"] for group in combinations):
            support.append("complete_three_branch_set")
        if route in ("jian_lu", "month_jie", "yang_blade"):
            status = "special_route_review"
        elif route == "mixed_qi":
            status = "supported_for_review" if support else "deferred_without_selection_evidence"
        else:
            status = "ordinary_candidate"
        selection.append({"candidate_id": candidate["id"], "label": candidate["label"],
                          "status": status, "support": support})
    visible = [
        {"position": p["position"], **p["heavenly_stem"]}
        for p in facts["pillars"] if p["position"] != "日柱"
        and p["heavenly_stem"]["ten_god"] in ("正财", "偏财", "正官", "七杀", "食神")
    ]
    return {
        "route": route, "label": label, "status": "research_only", "source_ids": source_ids,
        "mapping_note": maps["mapping_note"], "month_combinations": combinations,
        "candidate_selection": selection, "visible_coordination": visible,
        "unresolved": ["会支是否实际合化及合冲竞争", "兼透兼会的取舍与有情无情",
                       "特殊路径中的财官煞食及其他四柱配合", "旺衰、成败救应和最终取用"],
        "limitations": "筛选仅安排核查方向，不删除原候选，不判三合化局、成格或喜用神；无筛选证据不表示该星不存在。",
    }


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
                            "reason":"月令含同类，参见候选筛选中的禄劫刃月支条件；藏干含比劫本身不能自动定格。"})
            continue
        candidates.append({"id":"month-hidden-"+hidden["stem"],"label":rules["pattern_labels"][hidden["ten_god"]],
                           "month_branch":facts["month_branch"],"stem":hidden["stem"],"ten_god":hidden["ten_god"],
                           "transmitted":bool(positions),"visible_positions":positions,"status":"candidate_only",
                           "source_ids":["ziping-yongshen-month-origin","ziping-yongshen-pillar-coordination"],
                           "conditions_to_check":["月令取用的实际适用条件","多藏干与透干的取舍","整体旺衰","其他干支的成败救应"]})
    selection = select_research_paths(facts, candidates, rules)
    trace=[
        {"rule":"month-season","description":"按节气月支作季节标签；季末月不直接判土旺或得令", "source_ids":["ziping-season-not-final"]},
        {"rule":"root-observation","description":"逐柱列出同干与同五行藏干位置，不给根力分数", "source_ids":["ziping-root-observation"]},
        {"rule":"month-transmission","description":"月支藏干与非日干逐字比对，记录透出位置", "source_ids":["ziping-yongshen-pillar-coordination"]},
        {"rule":"pattern-study-candidates","description":"按月支藏干十神给出研究候选，不排名、不宣称成格", "source_ids":["ziping-yongshen-month-origin","ziping-yongshen-pillar-coordination"]},
        {"rule":"research-path-selection","description":selection["label"] + "；仅筛选核查方向", "source_ids":selection["source_ids"]},
    ]
    return {"method_version":rules["version"],"day_master":chart.day_master,
            "season":{"month_branch":facts["month_branch"],"label":season,"associated_element":dominant,
                      "relation_to_day_master":season_relation,"strength_status":"unassessed"},
            "roots":roots,"month_transmission":transmission,"pattern_candidates":candidates,
            "special_case_flags":special,"trace":trace,"unresolved":rules["unresolved"],
            "research_selection":selection,
            "strength_conclusion":"undetermined","pattern_conclusion":"undetermined","useful_god_conclusion":"undetermined",
            "limitations":"程序已计算关系与候选，尚未判定根力、整体旺衰、最终格局、喜用神或大运；列表顺序不是优先级。"}
