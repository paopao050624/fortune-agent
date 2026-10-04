"""Compare saved baseline and sourced tarot evaluations without new API calls."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .evaluation import automatic_checks, load_cases


def read_results(path: Path) -> dict[str, dict]:
    records = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        case_id = record["case_id"]
        if case_id in records:
            raise ValueError(f"Duplicate case ID in {path}: {case_id}")
        records[case_id] = record
    return records


def compare(baseline: Path, sourced: Path, cases_path: Path) -> list[dict[str, object]]:
    base_results = read_results(baseline)
    source_results = read_results(sourced)
    cases = {case.id: case for case in load_cases(cases_path)}
    rows = []
    for case_id in sorted(base_results.keys() & source_results.keys()):
        case = cases[case_id]
        expected = case.reading()
        expected_data = json.loads(json.dumps(asdict(expected), ensure_ascii=False))
        base = base_results[case_id]
        source = source_results[case_id]
        if (
            base["reading"] != source["reading"]
            or base["reading"] != expected_data
            or base["style"] != source["style"]
            or base["style"] != case.style
            or base.get("model") != source.get("model")
        ):
            raise ValueError(f"Inputs differ for {case_id}")
        cited = [item for item in source.get("evidence", []) if item["status"] == "sourced"]
        rows.append({
            "case_id": case_id,
            "baseline": automatic_checks(expected, base["interpretation"]),
            "sourced": automatic_checks(expected, source["interpretation"]),
            "source_citations": sum(item["source_url"] in source["interpretation"] for item in cited),
            "source_count": len(cited),
        })
    if not rows:
        raise ValueError("No common case IDs to compare")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="比较塔罗 Agent 的两组已保存评估结果")
    parser.add_argument("baseline", type=Path)
    parser.add_argument("sourced", type=Path)
    parser.add_argument("--cases", type=Path, default=Path("evals/cases.json"))
    args = parser.parse_args()
    rows = compare(args.baseline, args.sourced, args.cases)
    print("案例 | 基线牌名覆盖 | 带来源牌名覆盖 | 基线确定性词 | 带来源确定性词 | 来源链接")
    print("--- | --- | --- | --- | --- | ---")
    for row in rows:
        base = row["baseline"]
        source = row["sourced"]
        print(
            f"{row['case_id']} | {base['card_name_coverage']:.0%} | "
            f"{source['card_name_coverage']:.0%} | "
            f"{'是' if base['certainty_phrase_found'] else '否'} | "
            f"{'是' if source['certainty_phrase_found'] else '否'} | "
            f"{row['source_citations']}/{row['source_count']}"
        )


if __name__ == "__main__":
    main()
