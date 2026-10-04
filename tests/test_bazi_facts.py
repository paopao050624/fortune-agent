import importlib.util
import unittest
from types import SimpleNamespace

from fortune_agent.bazi_facts import HIDDEN_STEMS, STEMS, chart_facts, ten_god


class BaziFactTests(unittest.TestCase):
    def test_yang_and_yin_day_masters_have_different_relationships(self):
        self.assertEqual(ten_god("甲", "丙"), "食神")
        self.assertEqual(ten_god("乙", "丙"), "伤官")
        self.assertEqual(ten_god("甲", "辛"), "正官")
        self.assertEqual(ten_god("乙", "辛"), "七杀")

    @unittest.skipUnless(importlib.util.find_spec("lunar_python"), "optional calculator absent")
    def test_all_hundred_relationships_and_hidden_stems_match_pinned_library(self):
        from lunar_python.util.LunarUtil import LunarUtil
        for master in STEMS:
            for stem in STEMS:
                with self.subTest(master=master, stem=stem):
                    self.assertEqual(ten_god(master, stem), LunarUtil.SHI_SHEN[master + stem])
        self.assertEqual({branch: list(stems) for branch, stems in HIDDEN_STEMS.items()}, LunarUtil.ZHI_HIDE_GAN)

    def test_month_branch_and_day_master_label_are_preserved(self):
        chart = SimpleNamespace(year="己卯", month="丙子", day="戊午", hour="戊午", day_master="戊")
        facts = chart_facts(chart)
        self.assertEqual(facts["month_branch"], "子")
        self.assertEqual(facts["pillars"][2]["heavenly_stem"]["role"], "日主")
        self.assertEqual(facts["pillars"][1]["hidden_stems"][0]["ten_god"], "正财")

    def test_invalid_stems_are_rejected(self):
        for master, stem in (("", "甲"), ("甲", "甲乙"), ("不存在", "甲")):
            with self.assertRaises(ValueError):
                ten_god(master, stem)


if __name__ == "__main__":
    unittest.main()
