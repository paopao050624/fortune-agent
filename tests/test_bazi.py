import importlib.util
import json
import unittest
from datetime import date
from types import SimpleNamespace

from fortune_agent.bazi import calculate_bazi
from fortune_agent.bazi_agent import interpret_bazi


HAS_LUNAR = importlib.util.find_spec("lunar_python") is not None


class BaziTests(unittest.TestCase):
    def test_rejects_unsupported_timezone_and_missing_offset(self):
        for birth, zone in (
            ("2000-01-01T12:00:00+08:00", "America/New_York"),
            ("2000-01-01T12:00:00", "Asia/Shanghai"),
            ("2000-01-01T12:00:00+00:00", "Asia/Shanghai"),
        ):
            with self.subTest(birth=birth, zone=zone), self.assertRaises(ValueError):
                calculate_bazi(birth, zone)

    @unittest.skipUnless(HAS_LUNAR, "lunar-python optional dependency absent")
    def test_lichun_changes_year_and_month_at_exact_boundary(self):
        before = calculate_bazi("2026-02-04T04:01:00+08:00")
        after = calculate_bazi("2026-02-04T04:03:00+08:00")
        self.assertEqual((before.year, before.month), ("乙巳", "己丑"))
        self.assertEqual((after.year, after.month), ("丙午", "庚寅"))
        self.assertEqual(after.previous_jie_time, "2026-02-04 04:02:08")
        self.assertEqual(before.day, after.day)

    @unittest.skipUnless(HAS_LUNAR, "lunar-python optional dependency absent")
    def test_2300_changes_hour_but_not_day_under_sect_two(self):
        before = calculate_bazi("2026-10-04T22:59:00+08:00")
        after = calculate_bazi("2026-10-04T23:01:00+08:00")
        self.assertEqual(before.day, after.day)
        self.assertNotEqual(before.hour, after.hour)
        next_day = calculate_bazi("2026-10-05T00:01:00+08:00")
        self.assertNotEqual(after.day, next_day.day)

    @unittest.skipUnless(HAS_LUNAR, "lunar-python optional dependency absent")
    def test_model_gets_calculated_pillars_and_rules(self):
        chart = calculate_bazi("2000-01-01T12:00:00+08:00")

        class FakeResponses:
            def __init__(self):
                self.request = None

            def create(self, **kwargs):
                self.request = kwargs
                return SimpleNamespace(output_text="这是反思提示。")

        responses = FakeResponses()
        answer = interpret_bazi(
            chart, "学习上应注意什么？", SimpleNamespace(responses=responses), "test-model",
            reference_date=date(2030, 12, 31),
        )
        self.assertEqual(answer, "这是反思提示。")
        self.assertIn(chart.year, str(responses.request["input"]))
        self.assertIn("未做真太阳时校正", str(responses.request["input"]))
        self.assertFalse(responses.request["store"])
        payload = json.loads(responses.request["input"][0]["content"])
        self.assertEqual(payload["reference_date"], "2030-12-31")
        self.assertNotEqual(payload["reference_date"], chart.birth_time[:10])
        self.assertEqual(payload["source_evidence"][0]["stem"], chart.day_master)
        self.assertIn("oldid=", payload["source_evidence"][0]["source_url"])
        self.assertEqual(payload["style"],"gentle")


if __name__ == "__main__":
    unittest.main()
