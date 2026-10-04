import importlib.util
import json
from datetime import date
from types import SimpleNamespace
import unittest

from fortune_agent.bazi import parse_bazi_pillars
from fortune_agent.bazi_daily import daily_bazi_context
from fortune_agent.bazi_agent import interpret_bazi


@unittest.skipUnless(importlib.util.find_spec("lunar_python"),"optional calculator absent")
class DailyBaziTests(unittest.TestCase):
    def chart(self):return parse_bazi_pillars("己卯 丙子 戊午 戊午")

    def test_fixed_date_keeps_facts_without_inventing_natal_birth(self):
        chart=self.chart()
        first=daily_bazi_context(chart,date(2026,10,4))
        self.assertEqual(first,daily_bazi_context(chart,date(2026,10,4)))
        self.assertIsNone(chart.birth_time)
        self.assertEqual(first["pillars"][2]["ganzhi"],"辛亥")
        self.assertEqual(first["pillars"][2]["heavenly_stem"]["ten_god"],"伤官")
        self.assertEqual(first["reference_time"],"2026-10-04T12:00:00+08:00")
        self.assertEqual(len(first["pillars"]),3)

    def test_next_day_changes_daily_branch_and_not_natal_master(self):
        before=daily_bazi_context(self.chart(),date(2026,10,4))
        after=daily_bazi_context(self.chart(),date(2026,10,5))
        self.assertNotEqual(before["pillars"][2]["ganzhi"],after["pillars"][2]["ganzhi"])
        self.assertEqual(after["natal_day_master"],"戊")

    def test_lichun_reference_uses_noon_and_shows_term_boundary(self):
        before=daily_bazi_context(self.chart(),date(2026,2,3))
        after=daily_bazi_context(self.chart(),date(2026,2,4))
        self.assertEqual(before["pillars"][0]["ganzhi"],"乙巳")
        self.assertEqual(after["pillars"][0]["ganzhi"],"丙午")
        self.assertEqual(after["previous_jie_time"],"2026-02-04 04:02:08")

    def test_model_receives_natal_and_daily_data_separately(self):
        class Responses:
            def create(self,**kwargs):
                self.request=kwargs
                return SimpleNamespace(output_text="不判断今日吉凶。")
        responses=Responses()
        context=daily_bazi_context(self.chart(),date(2026,10,4))
        interpret_bazi(self.chart(),"今天学习怎么安排？",SimpleNamespace(responses=responses),"test-model",
                       reference_date=date(2026,10,4),daily_context=context)
        payload=json.loads(responses.request["input"][0]["content"])
        self.assertEqual(payload["chart"]["day"],"戊午")
        self.assertEqual(payload["daily_context"]["pillars"][2]["ganzhi"],"辛亥")
        self.assertIn("不能评分或判断吉凶",responses.request["instructions"])
        self.assertFalse(responses.request["store"])


if __name__=="__main__":unittest.main()
