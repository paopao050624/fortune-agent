"""Command-line interface for the first-version four-pillar calculator."""

from __future__ import annotations

import argparse
import json
from datetime import date
from dataclasses import asdict

from .bazi import calculate_bazi, parse_bazi_pillars
from .bazi_sources import evidence_for
from .bazi_facts import chart_facts
from .bazi_rules import wealth_checklist
from .bazi_daily import daily_bazi_context
from .bazi_structure import analyze_structure


def main() -> None:
    parser = argparse.ArgumentParser(description="八字四柱排盘原型")
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--birth", help="公历出生时刻，例如 2000-01-01T12:00:00+08:00")
    inputs.add_argument("--pillars", help="直接提供四柱，例如 '己卯 丙子 戊午 戊午'")
    parser.add_argument("--timezone", default="Asia/Shanghai")
    parser.add_argument("--interpret", help="可选：要问模型的问题")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--sources", action="store_true", help="显示日主对应的原文和出处，无需 API")
    parser.add_argument("--details", action="store_true", help="显示程序计算的十神与藏干，无需 API")
    parser.add_argument("--analysis", action="store_true", help="显示财格方法条件清单，无需 API")
    parser.add_argument("--structure",action="store_true",help="显示月令、通根、透干与格局研究候选")
    parser.add_argument("--daily",action="store_true",help="查看今日干支与本命日主关系")
    parser.add_argument("--date",type=date.fromisoformat,help="每日参考公历日期，需同时使用 --daily")
    args = parser.parse_args()
    if args.date is not None and not args.daily:
        parser.error("--date 须配合 --daily")
    try:
        chart = parse_bazi_pillars(args.pillars) if args.pillars else calculate_bazi(args.birth, args.timezone)
        evidence = evidence_for(chart)
        facts = chart_facts(chart)
        checklist = wealth_checklist(chart)
        structure=analyze_structure(chart)
        daily_context=daily_bazi_context(chart,args.date) if args.daily else None
        interpretation = None
        if args.interpret:
            from .config import ApiConfig
            config = ApiConfig.from_env()
            try:
                from openai import APIError, APIStatusError, OpenAI
            except ImportError:
                parser.error("请先安装 Agent 依赖：pip install -e '.[agent,bazi]'")
            from .bazi_agent import interpret_bazi
            try:
                interpretation = interpret_bazi(
                    chart, args.interpret,
                    OpenAI(api_key=config.api_key, base_url=config.base_url, timeout=60, max_retries=0), config.model,
                    reference_date=args.date,daily_context=daily_context,
                )
            except APIStatusError as exc:
                parser.exit(1, f"中转站请求失败：HTTP {exc.status_code}，错误码 {exc.code or 'unknown'}。\n")
            except APIError as exc:
                parser.exit(1, f"中转站连接失败：{type(exc).__name__}。\n")
    except (ValueError, RuntimeError) as exc:
        parser.error(str(exc))

    if args.json:
        print(json.dumps({"chart": asdict(chart), "derived_facts": facts,
                          "method_checklist": checklist, "interpretation": interpretation,
                          "evidence": evidence,"daily_context":daily_context,
                          "structural_analysis":structure}, ensure_ascii=False, indent=2))
        return
    if chart.birth_time is not None:
        print(f"出生时间：{chart.birth_time}（{chart.timezone}）")
    else:
        print(f"资料来源：{chart.calculator}")
    print(f"四柱：{chart.year} {chart.month} {chart.day} {chart.hour}")
    print(f"日主：{chart.day_master}")
    if chart.previous_jie is not None:
        print(f"前一节：{chart.previous_jie} {chart.previous_jie_time}")
        print(f"后一节：{chart.next_jie} {chart.next_jie_time}")
    print(f"规则：{chart.day_boundary_rule}；{chart.solar_time_rule}")
    if args.structure:
        season=structure["season"]
        print(f"\n月令结构：{season['month_branch']}月，{season['label']}；季节关联五行 {season['associated_element'] or '季末月不统一判旺'}")
        for root in structure["roots"]:
            found="、".join(f"{item['position']}{item['branch']}藏{item['hidden_stem']}（{'同干' if item['match']=='same_stem' else '同五行'}）" for item in root["locations"])
            print(f"{root['position']}天干{root['stem']}根气观察：{found or '四支未见同五行藏干'}；根力未判定")
        for hidden in structure["month_transmission"]:
            print(f"月支藏{hidden['stem']}（{hidden['ten_god']}）：{'、'.join(hidden['visible_positions']) or '未见非日干透出'}")
        for candidate in structure["pattern_candidates"]:
            print(f"研究方向：{candidate['label']}，据月支藏{candidate['stem']}；仅候选")
        for flag in structure["special_case_flags"]:
            print(flag["reason"])
        selection = structure["research_selection"]
        print(f"候选筛选：{selection['label']}；仅研究路径")
        for item in selection["candidate_selection"]:
            labels = {"supported_for_review": "已有筛选证据，继续核查", "deferred_without_selection_evidence": "尚缺筛选证据", "special_route_review": "转入特殊路径核查", "ordinary_candidate": "普通候选"}
            support = "、".join("同干透出" if value == "exact_transmission" else "完整三合支字组合" for value in item["support"])
            print(f"{item['label']}：{labels[item['status']]}；{support or '无额外筛选证据'}")
        for group in selection["month_combinations"]:
            print(f"{''.join(group['branches'])}三合支字齐备；未判合化")
        print(selection["limitations"])
        interactions = structure["interactions"]
        print("干支关系观察（效力未判定）：")
        for item in interactions["observations"]:
            locations = " → ".join(p + c for p, c in zip(item["positions"], item["characters"]))
            print(f"{item['kind']}：{locations}")
        for group in interactions["complete_punishment_groups"]:
            print(f"{''.join(group['branches'])}三刑支字齐备；未判效力")
        print(f"根气关联待核查 {len(interactions['root_reviews'])} 项；不自动删根或定格")
        print(interactions["limitations"])
        print(structure["limitations"])
    if daily_context:
        print(f"\n每日八字参考：{daily_context['date']}（中国标准时间12:00）")
        for pillar in daily_context["pillars"]:
            stem=pillar["heavenly_stem"]
            hidden="、".join(f"{item['stem']}（{item['ten_god']}）" for item in pillar["hidden_stems"])
            print(f"{pillar['position']} {pillar['ganzhi']}：相对本命日主{chart.day_master}，天干{stem['ten_god']}；藏干{hidden}")
        print(daily_context["limitations"])
    if args.details:
        print(f"\n月令月支：{facts['month_branch']}")
        for pillar in facts["pillars"]:
            stem = pillar["heavenly_stem"]
            relationship = stem.get("role", stem["ten_god"])
            hidden = "、".join(f"{item['stem']}（{item['ten_god']}）" for item in pillar["hidden_stems"])
            print(f"{pillar['position']} {pillar['ganzhi']}：天干 {stem['polarity']}{stem['element']} {relationship}；藏干 {hidden}")
        print(f"方法边界：{facts['limitations']}")
    if args.analysis:
        print("\n财格方法条件清单（尚不能确定格局）：")
        month_wealth = "、".join(f"{item['stem']}（{item['ten_god']}）" for item in checklist["month_wealth_hidden_stems"])
        print(f"月支 {checklist['month_branch']} 的财星藏干：{month_wealth or '未见；不作格局排除判断'}")
        for observation in checklist["observations"].values():
            found = "、".join(f"{item['position']} {item['stem']}（{item['ten_god']}）" for item in observation["stems"])
            print(f"{observation['label']}：{found or '未见透干；不代表藏干中没有'}")
        for path in checklist["paths"]:
            print(f"路径：{path['label']}；待核实：{'、'.join(path['unverified_conditions'])}")
        print(checklist["limitations"])
        source = next(entry for entry in evidence if entry["id"] == checklist["source_id"])
        print(f"条件出处：{source['locator']}\n{source['source_url']}")
    if interpretation:
        print(f"\n解读：\n{interpretation}")
    if args.sources or interpretation:
        for entry in evidence:
            print(f"\n原文：{entry['source_text']}")
            print(f"出处：《{entry['work']}》{entry['locator']}\n{entry['source_url']}")
            print(f"版本说明：{entry['edition_note']}")
            if entry.get("punctuation_policy"):
                print(f"句读说明：{entry['punctuation_policy']}")
            for note in entry["notes"]:
                print(f"校勘提示：{note}")


if __name__ == "__main__":
    main()
