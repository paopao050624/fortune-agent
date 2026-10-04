import importlib.util
import json
import tempfile
import unittest
from dataclasses import asdict, replace
from datetime import date
from pathlib import Path

from fortune_agent.bazi_evaluation import automatic_checks, load_cases
from fortune_agent.bazi_agent import PROMPT_SHA256
from fortune_agent.bazi_eval_runner import completed_cases
from fortune_agent.bazi_sources import catalog_sha256
from fortune_agent.bazi_facts import chart_facts
from fortune_agent.bazi_rules import wealth_checklist


CASES = Path(__file__).resolve().parents[1] / "evals" / "bazi_cases.json"
EXPECTED = CASES.with_name("bazi_expected.json")
HAS_LUNAR = importlib.util.find_spec("lunar_python") is not None


class BaziEvaluationTests(unittest.TestCase):
    def test_case_inventory(self):
        cases = load_cases(CASES)
        self.assertEqual(len(cases), 12)
        self.assertEqual(len({case.id for case in cases}), 12)
        self.assertEqual(
            {case.topic for case in cases},
            {"education", "career", "boundary", "health", "finance", "certainty", "citation", "method", "legal"},
        )

    @unittest.skipUnless(HAS_LUNAR, "lunar-python optional dependency absent")
    def test_checks_flag_unexpected_pillars(self):
        chart = load_cases(CASES)[0].chart()
        checks = automatic_checks(chart, "四柱是甲子、乙丑、丙寅、丁卯，日主戊。未做真太阳时校正。")
        self.assertIn("甲子", checks["unexpected_pillars"])
        self.assertTrue(checks["true_solar_time_limit_mentioned"])

    @unittest.skipUnless(HAS_LUNAR, "lunar-python optional dependency absent")
    def test_all_synthetic_charts_match_checked_in_fixtures(self):
        expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
        actual = [
            {"case_id": case.id, "chart": asdict(case.chart())}
            for case in load_cases(CASES)
        ]
        self.assertEqual(actual, expected)

    @unittest.skipUnless(HAS_LUNAR, "lunar-python optional dependency absent")
    def test_resume_rejects_changed_question_date_and_prompt(self):
        case = load_cases(CASES)[0]
        reference_date = date(2026, 10, 4)
        record = {
            "case_id": case.id, "model": "test-model", "chart": asdict(case.chart()),
            "question": case.question, "topic": case.topic,
            "reference_date": reference_date.isoformat(), "prompt_sha256": PROMPT_SHA256,
            "source_catalog_sha256": catalog_sha256(),
            "derived_facts": chart_facts(case.chart()),
            "method_checklist": wealth_checklist(case.chart()),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.jsonl"
            path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
            self.assertEqual(completed_cases(path, [case], "test-model", reference_date), {case.id})
            with self.assertRaises(ValueError):
                completed_cases(path, [replace(case, question="新的问题")], "test-model", reference_date)
            with self.assertRaises(ValueError):
                completed_cases(path, [case], "test-model", date(2026, 10, 5))
            record["prompt_sha256"] = "old-prompt"
            path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                completed_cases(path, [case], "test-model", reference_date)
            record["prompt_sha256"] = PROMPT_SHA256
            record["source_catalog_sha256"] = "old-source-data"
            path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                completed_cases(path, [case], "test-model", reference_date)


if __name__ == "__main__":
    unittest.main()
