import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from fortune_agent.evaluation import automatic_checks, load_cases
from fortune_agent.eval_runner import completed_cases


CASES = Path(__file__).resolve().parents[1] / "evals" / "cases.json"


class EvaluationTests(unittest.TestCase):
    def test_all_cases_have_valid_fixed_readings(self):
        cases = load_cases(CASES)
        self.assertEqual(len(cases), 20)
        self.assertEqual(len({case.id for case in cases}), 20)
        for case in cases:
            with self.subTest(case=case.id):
                reading = case.reading()
                self.assertEqual(len(reading.cards), len(case.cards))
                self.assertEqual(len({item.card.id for item in reading.cards}), len(case.cards))

    def test_automatic_checks_identify_missing_card_and_certain_prediction(self):
        reading = load_cases(CASES)[1].reading()
        checks = automatic_checks(reading, "皇后逆位提示你休息，但下周一定会成功。")
        self.assertFalse(checks["all_card_names_present"])
        self.assertTrue(checks["certainty_phrase_found"])

    def test_negated_prediction_is_not_flagged(self):
        reading = load_cases(CASES)[0].reading()
        checks = automatic_checks(reading, "恶魔正位可供反思，不代表你一定会拖延。")
        self.assertFalse(checks["certainty_phrase_found"])
        checks = automatic_checks(reading, "这张牌不预示这周一定会发生什么。")
        self.assertFalse(checks["certainty_phrase_found"])
        checks = automatic_checks(reading, "塔罗不是在预测你接下来一定会怎样。")
        self.assertFalse(checks["certainty_phrase_found"])

    def test_resume_rejects_changed_model_or_source_catalog(self):
        case = load_cases(CASES)[0]
        record = {
            "case_id": case.id, "variant": "sourced", "model": "test-model",
            "source_catalog_sha256": "hash-1", "style": case.style,
            "reading": asdict(case.reading()),
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "results.jsonl"
            output.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
            self.assertEqual(completed_cases(output, "sourced", "test-model", [case], "hash-1"), {case.id})
            with self.assertRaisesRegex(ValueError, "不一致"):
                completed_cases(output, "sourced", "other-model", [case], "hash-1")
            with self.assertRaisesRegex(ValueError, "不一致"):
                completed_cases(output, "sourced", "test-model", [case], "hash-2")


if __name__ == "__main__":
    unittest.main()
