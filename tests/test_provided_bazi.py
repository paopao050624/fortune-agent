import json
import unittest
from datetime import date
from types import SimpleNamespace

from fortune_agent.bazi import parse_bazi_pillars
from fortune_agent.bazi_agent import interpret_bazi
from fortune_agent.bazi_facts import chart_facts
from fortune_agent.bazi_rules import wealth_checklist


class ProvidedPillarTests(unittest.TestCase):
    def test_separated_and_compact_inputs_have_same_result(self):
        expected = parse_bazi_pillars("己卯 丙子 戊午 戊午")
        for text in ("己卯丙子戊午戊午", " 己卯，丙子、戊午\n戊午 "):
            self.assertEqual(parse_bazi_pillars(text), expected)
        self.assertEqual(expected.day_master, "戊")
        self.assertIsNone(expected.birth_time)
        self.assertIsNone(expected.previous_jie_time)
        self.assertIsNone(expected.timezone)

    def test_impossible_single_pillars_and_wrong_length_are_rejected(self):
        for text in ("", "甲丑 丙子 戊午 戊午", "己卯 丙子 戊午", "己卯 丙子 戊午 戊午 甲子", "abcd efgh"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_bazi_pillars(text)

    def test_provided_pillars_reuse_facts_and_unknown_rule_conditions(self):
        chart = parse_bazi_pillars("己卯 丙子 戊午 戊午")
        self.assertEqual(chart_facts(chart)["month_branch"], "子")
        self.assertEqual(wealth_checklist(chart)["conclusion"], "undetermined")

    def test_model_receives_unknown_time_and_supplied_provenance(self):
        class Responses:
            def create(self, **kwargs):
                self.request = kwargs
                return SimpleNamespace(output_text="四柱由用户提供，出生时间未知。")
        responses = Responses()
        interpret_bazi(parse_bazi_pillars("己卯 丙子 戊午 戊午"), "解释资料", SimpleNamespace(responses=responses),
                       "test-model", date(2026, 10, 4))
        payload = json.loads(responses.request["input"][0]["content"])
        self.assertIsNone(payload["chart"]["birth_time"])
        self.assertIn("用户提供", payload["chart"]["calculator"])
        self.assertIn("不得虚构", responses.request["instructions"])


if __name__ == "__main__":
    unittest.main()
