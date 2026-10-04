"""Command-line interface for the first-version four-pillar calculator."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .bazi import calculate_bazi, parse_bazi_pillars
from .bazi_sources import evidence_for
from .bazi_facts import chart_facts
from .bazi_rules import wealth_checklist


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
    args = parser.parse_args()
    try:
        chart = parse_bazi_pillars(args.pillars) if args.pillars else calculate_bazi(args.birth, args.timezone)
        evidence = evidence_for(chart)
        facts = chart_facts(chart)
        checklist = wealth_checklist(chart)
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
                          "evidence": evidence}, ensure_ascii=False, indent=2))
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
