"""Run and save synthetic birth-chart interpretation cases."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path

from .bazi_agent import PROMPT_SHA256, current_reference_date, interpret_bazi
from .bazi_evaluation import automatic_checks, load_cases
from .config import ApiConfig
from .bazi_sources import catalog_sha256, evidence_for
from .bazi_facts import chart_facts
from .bazi_rules import wealth_checklist
from .bazi_structure import analyze_structure


def completed_cases(path: Path, cases: list, model: str, reference_date: date) -> set[str]:
    selected = {case.id: case for case in cases}
    completed = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        case = selected.get(record["case_id"])
        if (
            case is None or case.id in completed
            or record.get("model") != model
            or record.get("chart") != asdict(case.chart())
            or record.get("question") != case.question
            or record.get("topic") != case.topic
            or record.get("reference_date") != reference_date.isoformat()
            or record.get("prompt_sha256") != PROMPT_SHA256
            or record.get("source_catalog_sha256") != catalog_sha256()
            or record.get("derived_facts") != chart_facts(case.chart())
            or record.get("method_checklist") != wealth_checklist(case.chart())
            or record.get("structural_analysis") != analyze_structure(case.chart())
        ):
            raise ValueError(f"已有结果与当前案例、模型、参考日期或提示词不一致：{record.get('case_id')}")
        completed.add(case.id)
    return completed


def main() -> None:
    parser = argparse.ArgumentParser(description="运行八字 Agent 合成案例评估")
    parser.add_argument("--cases", type=Path, default=Path("evals/bazi_cases.json"))
    parser.add_argument("--case-id", help="只运行指定案例 ID")
    parser.add_argument("--limit", type=int, default=None, help="最多运行前 N 例")
    parser.add_argument("--timeout", type=float, default=30.0, help="每次请求的等待秒数，默认 30")
    parser.add_argument("--reference-date", type=date.fromisoformat, default=current_reference_date(), help="相对日期参考点，例如 2026-10-04")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit 必须大于 0")
    if not 0 < args.timeout <= 300:
        parser.error("--timeout 必须大于 0 且不超过 300 秒")
    all_cases = load_cases(args.cases)
    cases = [case for case in all_cases if case.id == args.case_id] if args.case_id else all_cases
    if not cases:
        parser.error(f"找不到案例：{args.case_id}")
    if args.limit is not None:
        cases = cases[:args.limit]
    try:
        config = ApiConfig.from_env()
    except ValueError as exc:
        parser.error(str(exc))
    from openai import APIError, APIStatusError, OpenAI

    client = OpenAI(
        api_key=config.api_key, base_url=config.base_url,
        timeout=args.timeout, max_retries=0,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    completed = set()
    if args.resume:
        if not args.output.exists():
            parser.error("续跑结果文件不存在")
        try:
            completed = completed_cases(args.output, cases, config.model, args.reference_date)
        except (KeyError, ValueError) as exc:
            parser.error(str(exc))
    with args.output.open("a" if args.resume else "x", encoding="utf-8") as stream:
        for case in cases:
            if case.id in completed:
                continue
            chart = case.chart()
            try:
                answer = interpret_bazi(chart, case.question, client, config.model, args.reference_date)
            except APIStatusError as exc:
                parser.exit(1, f"{case.id}: 中转站 HTTP {exc.status_code}，错误码 {exc.code or 'unknown'}；已完成结果保留在 {args.output}。\n")
            except APIError as exc:
                parser.exit(1, f"{case.id}: 中转站请求失败（{type(exc).__name__}）；已完成结果保留在 {args.output}。\n")
            record = {
                "case_id": case.id,
                "topic": case.topic,
                "question": case.question,
                "model": config.model,
                "reference_date": args.reference_date.isoformat(),
                "prompt_sha256": PROMPT_SHA256,
                "source_catalog_sha256": catalog_sha256(),
                "source_evidence": evidence_for(chart),
                "derived_facts": chart_facts(chart),
                "method_checklist": wealth_checklist(chart),
                "structural_analysis":analyze_structure(chart),
                "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
                "chart": asdict(chart),
                "answer": answer,
                "checks": automatic_checks(chart, answer),
            }
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            stream.flush()
            print(f"{case.id}: {record['checks']}", flush=True)
    print(f"结果：{args.output}")


if __name__ == "__main__":
    main()
