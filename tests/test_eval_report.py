import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from fortune_agent.eval_report import compare
from fortune_agent.evaluation import load_cases


CASES = Path(__file__).resolve().parents[1] / "evals" / "cases.json"


class ReportTests(unittest.TestCase):
    def test_comparison_uses_same_fixed_reading_and_current_checks(self):
        case = load_cases(CASES)[0]
        reading = asdict(case.reading())
        base = {"case_id": case.id, "style": case.style, "reading": reading,
                "interpretation": "恶魔正位不代表你一定会拖延。", "evidence": []}
        source = {**base, "interpretation": "恶魔正位可供反思。[出处](https://example.org/page)",
                  "evidence": [{"status": "sourced", "source_url": "https://example.org/page"}]}
        with tempfile.TemporaryDirectory() as directory:
            baseline_path = Path(directory) / "baseline.jsonl"
            sourced_path = Path(directory) / "sourced.jsonl"
            baseline_path.write_text(json.dumps(base, ensure_ascii=False) + "\n", encoding="utf-8")
            sourced_path.write_text(json.dumps(source, ensure_ascii=False) + "\n", encoding="utf-8")
            rows = compare(baseline_path, sourced_path, CASES)
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["baseline"]["certainty_phrase_found"])
        self.assertEqual(rows[0]["source_citations"], 1)

    def test_comparison_rejects_matching_but_wrong_cards(self):
        case = load_cases(CASES)[0]
        wrong_reading = asdict(case.reading())
        wrong_reading["cards"][0]["card"]["id"] = "major-01"
        record = {"case_id": case.id, "style": case.style, "model": "test-model",
                  "reading": wrong_reading, "interpretation": "恶魔正位", "evidence": []}
        with tempfile.TemporaryDirectory() as directory:
            baseline_path = Path(directory) / "baseline.jsonl"
            sourced_path = Path(directory) / "sourced.jsonl"
            content = json.dumps(record, ensure_ascii=False) + "\n"
            baseline_path.write_text(content, encoding="utf-8")
            sourced_path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Inputs differ"):
                compare(baseline_path, sourced_path, CASES)


if __name__ == "__main__":
    unittest.main()
