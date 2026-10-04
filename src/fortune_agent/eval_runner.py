"""Run a small, fixed sample of live API evaluation cases."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .agent import TarotAgent
from .config import ApiConfig
from .evaluation import automatic_checks, load_cases
from .meanings import load_catalog


def completed_cases(output: Path, variant: str, model: str, cases: list, source_hash: str | None) -> set[str]:
    selected = {case.id: case for case in cases}
    completed = set()
    for line in output.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        case_id = record["case_id"]
        if case_id in completed or case_id not in selected:
            raise ValueError(f"结果文件含重复或不属于本次运行的案例：{case_id}")
        case = selected[case_id]
        expected_reading = json.loads(json.dumps(asdict(case.reading()), ensure_ascii=False))
        if (
            record.get("variant") != variant
            or record.get("model") != model
            or record.get("source_catalog_sha256") != source_hash
            or record.get("style") != case.style
            or record.get("reading") != expected_reading
        ):
            raise ValueError(f"结果文件与当前评估配置不一致：{case_id}")
        completed.add(case_id)
    return completed


def main() -> None:
    parser = argparse.ArgumentParser(description="运行塔罗 Agent 基线评估")
    parser.add_argument("--cases", type=Path, default=Path("evals/cases.json"))
    parser.add_argument("--case-id", help="只运行指定案例 ID")
    parser.add_argument("--limit", type=int, default=3, help="本次运行案例数，默认 3")
    parser.add_argument("--variant", choices=("baseline", "sourced"), default="baseline")
    parser.add_argument("--output", type=Path, required=True, help="新建 JSONL 结果文件")
    parser.add_argument("--resume", action="store_true", help="核对并续跑已有结果文件")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit 必须大于 0")
    all_cases = load_cases(args.cases)
    cases = [case for case in all_cases if case.id == args.case_id] if args.case_id else all_cases[:args.limit]
    if not cases:
        parser.error(f"找不到案例：{args.case_id}")
    try:
        config = ApiConfig.from_env()
    except ValueError as exc:
        parser.error(str(exc))

    from openai import OpenAI

    client = OpenAI(api_key=config.api_key, base_url=config.base_url)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    source_hash = (
        hashlib.sha256(json.dumps(load_catalog(), sort_keys=True).encode("utf-8")).hexdigest()
        if args.variant == "sourced" else None
    )
    if args.resume:
        if not args.output.exists():
            parser.error("续跑结果文件不存在")
        try:
            completed = completed_cases(args.output, args.variant, config.model, cases, source_hash)
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            parser.error(str(exc))
    else:
        completed = set()
    with args.output.open("a" if args.resume else "x", encoding="utf-8") as stream:
        for case in cases:
            if case.id in completed:
                print(f"{case.id}: 已完成，跳过", flush=True)
                continue
            fixed_reading = case.reading()
            agent = TarotAgent(
                client, config.model, draw=lambda *_: fixed_reading,
                use_sources=args.variant == "sourced",
            )
            result = agent.read(case.question, case.spread, style=case.style)
            record = {
                "case_id": case.id,
                "variant": args.variant,
                "model": config.model,
                "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
                "source_catalog_sha256": source_hash,
                "topic": case.topic,
                "style": case.style,
                "reading": asdict(result.reading),
                "interpretation": result.interpretation,
                "evidence": result.evidence,
                "checks": automatic_checks(result.reading, result.interpretation),
            }
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            stream.flush()
            print(f"{case.id}: {record['checks']}", flush=True)
    print(f"结果：{args.output}")


if __name__ == "__main__":
    main()
