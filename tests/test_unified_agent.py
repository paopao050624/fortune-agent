import json
import importlib.util
from pathlib import Path
import tempfile
from threading import Lock
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fortune_agent.conversation import ConversationStore
from fortune_agent.unified_agent import UnifiedAgent, validate_route, birth_matches_user_text


def plan(action="read",method="tarot",**fields):
    result={"action":action,"method":method,"question":None,"birth":None,"pillars":None,
            "birth_timezone":None,"spread":None,"picks":None,"lines":None,"policy":None,
            "style":None,"reply":"请补充资料。"}
    result.update(fields);return result


class FakeResponses:
    def __init__(self,plans):
        self.plans=list(plans);self.calls=[]

    def create(self,**kwargs):
        self.calls.append(kwargs)
        tools=kwargs.get("tools",[])
        if tools and tools[0]["name"]=="choose_action":
            return SimpleNamespace(output=[SimpleNamespace(type="function_call",name="choose_action",
                                   arguments=json.dumps(self.plans.pop(0),ensure_ascii=False))])
        if kwargs.get("tool_choice")=={"type":"function","name":"draw_tarot"}:
            return SimpleNamespace(output=[SimpleNamespace(type="function_call",name="draw_tarot",arguments="{}",call_id="fixed-card")])
        if kwargs.get("text",{}).get("format",{}).get("name")=="iching_interpretation":
            content=json.loads(kwargs["input"][0]["content"])
            result={"summary":"结合已有卦象反思。","explanations":[{"passage_id":p["id"],"meaning":"传统语义。","application":"核实实际情况。"} for p in content["selection"]["passages"]],
                    "advice":["先检查资料。"],"limitations":["不是未来保证。"]}
            return SimpleNamespace(output_text=json.dumps(result,ensure_ascii=False))
        return SimpleNamespace(output_text="沿用已有结果，先完成一项具体任务。")


class UnifiedTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.store=ConversationStore()
        self.session=self.store.get()

    def tearDown(self):self.directory.cleanup()

    def agent(self,plans):
        responses=FakeResponses(plans)
        return UnifiedAgent(SimpleNamespace(responses=responses),"test-model",Path(self.directory.name)/"daily.sqlite3",Lock()),responses

    def test_tarot_clarification_then_read_and_followup_preserve_cards(self):
        agent,_=self.agent([plan(method="tarot"),plan(question="怎样安排学习？"),plan(action="followup",question="更具体的步骤")])
        first=agent.turn(self.session,"想算塔罗")
        self.assertEqual(first["status"],"needs_input")
        second=agent.turn(self.session,"怎样安排学习？")
        cards=second["result"]["reading"]["cards"]
        with patch("fortune_agent.unified_agent.draw_reading",side_effect=AssertionError("Do not redraw")):
            third=agent.turn(self.session,"能给更具体的步骤吗？")
        self.assertEqual(third["result"]["reading"]["cards"],cards)
        self.assertTrue(third["trace"][-1]["reused"])

    def test_iching_followup_preserves_cast_and_policy(self):
        agent,_=self.agent([plan(method="iching",question="项目怎么推进？",lines=[9]*6),plan(action="followup",method="iching")])
        first=agent.turn(self.session,"用周易看项目，六次都是9")
        with patch("fortune_agent.unified_agent.cast_coins",side_effect=AssertionError("Do not recast")):
            second=agent.turn(self.session,"用九是什么意思？")
        self.assertEqual(first["result"]["cast"],second["result"]["cast"])
        self.assertEqual(second["result"]["selection"]["passages"][0]["kind"],"用九")

    def test_policy_change_reselects_from_same_cast_without_new_throw(self):
        agent,_=self.agent([plan(method="iching",question="项目推进",lines=[9]*6),
                           plan(action="followup",method="iching",policy="all-moving-v1")])
        first=agent.turn(self.session,"周易看项目，六次都是9")
        second=agent.turn(self.session,"同一卦换成全部动爻并读")
        self.assertEqual(first["result"]["cast"],second["result"]["cast"])
        self.assertEqual(second["result"]["selection"]["policy"],"all-moving-v1")
        self.assertEqual(len(second["result"]["selection"]["passages"]),9)

    def test_model_misroutes_policy_change_but_program_prevents_recast(self):
        agent,_=self.agent([plan(method="iching",question="项目推进",lines=[9]*6),
                           plan(action="read",method="iching",policy="all-moving-v1")])
        first=agent.turn(self.session,"周易看项目，六次都是9")
        with patch("fortune_agent.unified_agent.cast_coins",side_effect=AssertionError("Do not recast")):
            second=agent.turn(self.session,"保持这次卦象，换成全部动爻并读")
        self.assertEqual(first["result"]["cast"],second["result"]["cast"])
        self.assertEqual(second["trace"][0]["model_action"],"read")
        self.assertEqual(second["trace"][0]["action"],"followup")

    def test_supplied_bazi_uses_real_user_pillars_and_keeps_time_unknown(self):
        agent,_=self.agent([plan(method="bazi",pillars="己卯 丙子 戊午 戊午",question="解释八字")])
        result=agent.turn(self.session,"八字是己卯 丙子 戊午 戊午，请解释")
        self.assertIsNone(result["result"]["chart"]["birth_time"])
        self.assertEqual(result["result"]["chart"]["day_master"],"戊")

    def test_invented_pillars_and_birth_clock_are_not_executed(self):
        agent,_=self.agent([plan(method="bazi",pillars="己卯 丙子 戊午 戊午")])
        result=agent.turn(self.session,"我只有出生年份2000年")
        self.assertEqual(result["status"],"needs_input")
        agent,_=self.agent([plan(method="bazi",birth="2000-01-01T00:00:00+08:00",birth_timezone="Asia/Shanghai")])
        result=agent.turn(self.store.get(),"我出生于2000年1月1日，中国标准时间，但不知道几点")
        self.assertEqual(result["status"],"needs_input")
        self.assertIn("时刻",result["reply"])

    def test_birth_timezone_is_not_inferred_from_daily_setting(self):
        agent,_=self.agent([plan(method="bazi",birth="2000-01-01T12:00:00+08:00",birth_timezone="Asia/Shanghai")])
        result=agent.turn(self.session,"2000年1月1日12:00出生",zone="Asia/Shanghai")
        self.assertEqual(result["status"],"needs_input")
        self.assertIn("明确确认",result["reply"])

    def test_normalized_birth_must_match_actual_date_and_clock(self):
        self.assertTrue(birth_matches_user_text("2000-01-01T12:00:00+08:00","2000年1月1日中午十二点，北京时间"))
        self.assertFalse(birth_matches_user_text("2001-01-01T12:00:00+08:00","2000年1月1日12:00"))
        self.assertFalse(birth_matches_user_text("2000-01-01T13:00:00+08:00","2000年1月1日12点"))
        self.assertFalse(birth_matches_user_text("2000-01-01T08:00:00+08:00","2000年1月1日 +08:00，但不知道几点"))

    @unittest.skipUnless(importlib.util.find_spec("lunar_python"),"optional calculator absent")
    def test_simple_yes_confirms_an_explicit_timezone_question(self):
        agent,_=self.agent([plan(method="bazi",birth="2000-01-01T12:00:00+08:00",birth_timezone="unknown"),
                           plan(action="clarify",method="bazi")])
        first=agent.turn(self.session,"2000年1月1日12:00出生")
        self.assertEqual(first["status"],"needs_input")
        self.assertIn("中国标准时间",first["reply"])
        second=agent.turn(self.session,"是的")
        self.assertEqual(second["status"],"completed")
        self.assertEqual(second["result"]["chart"]["day_master"],"戊")

    def test_hexagram_comparison_adds_background_without_changing_primary_passages(self):
        agent,_=self.agent([plan(method="iching",question="项目推进",lines=[9,8,7,6,7,8]),
                           plan(action="followup",method="iching")])
        first=agent.turn(self.session,"周易看项目，六次9 8 7 6 7 8")
        second=agent.turn(self.session,"主卦和变卦分别有什么提示？")
        self.assertEqual(first["result"]["cast"],second["result"]["cast"])
        self.assertEqual(second["result"]["selection"]["policy"],"moving-count-v1")
        primary_before=[p["id"] for p in first["result"]["selection"]["passages"] if p["primary"]]
        primary_after=[p["id"] for p in second["result"]["selection"]["passages"] if p["primary"]]
        self.assertEqual(primary_before,primary_after)
        self.assertEqual(len(second["result"]["selection"]["supplementary_ids"]),2)

    def test_method_switch_clears_tarot_question_before_bazi_clarification(self):
        agent,_=self.agent([plan(question="学习安排"),plan(method="bazi")])
        agent.turn(self.session,"塔罗看学习")
        result=agent.turn(self.session,"改成八字")
        self.assertEqual(result["status"],"needs_input")
        self.assertIsNone(self.session.artifact)
        self.assertNotIn("question",self.session.slots)

    def test_style_preference_survives_method_switch(self):
        agent,_=self.agent([plan(question="学习安排",style="direct"),plan(method="bazi")])
        agent.turn(self.session,"塔罗看学习，直接一些")
        agent.turn(self.session,"改用八字")
        self.assertEqual(self.session.slots["style"],"direct")

    def test_daily_read_reuses_first_cached_interpretation(self):
        agent,responses=self.agent([plan(method="daily"),plan(method="daily")])
        first=agent.turn(self.session,"今天运势怎么样？")
        second=agent.turn(self.session,"再看今天运势")
        self.assertTrue(second["result"]["cached"])
        self.assertEqual(first["result"]["interpretation"],second["result"]["interpretation"])
        self.assertEqual(len(responses.calls),4) # Two routing calls, one two-step first read.

    def test_returned_data_cannot_mutate_internal_daily_identity(self):
        agent,_=self.agent([plan(method="daily"),plan(action="followup",method="daily")])
        first=agent.turn(self.session,"今天运势怎么样？")
        first["result"].pop("profile_key")
        self.assertIn("profile_key",self.session.artifact.data)
        second=agent.turn(self.session,"给一个小步骤")
        self.assertTrue(second["trace"][-1]["reused"])

    def test_route_types_and_unsupported_method_are_rejected(self):
        invalid=plan();invalid["picks"]=[True]
        with self.assertRaises(ValueError):validate_route(invalid)
        invalid=plan();invalid["method"]="ziwei"
        with self.assertRaises(ValueError):validate_route(invalid)

    def test_explicit_new_draw_runs_tool_again(self):
        agent,_=self.agent([plan(question="学习"),plan(question="学习")])
        agent.turn(self.session,"塔罗看学习")
        result=agent.turn(self.session,"重新抽牌看看学习")
        self.assertFalse(result["trace"][1]["reused"])

    def test_unsupported_feature_has_clear_reply(self):
        agent,_=self.agent([plan(action="unsupported",method="none")])
        result=agent.turn(self.session,"排紫微斗数")
        self.assertEqual(result["status"],"answered")
        self.assertIn("尚未实现",result["reply"])


class ConversationTests(unittest.TestCase):
    def test_cleared_and_expired_sessions_cannot_be_retrieved(self):
        store=ConversationStore(ttl=1)
        session=store.get();store.clear(session.id)
        with self.assertRaises(ValueError):store.get(session.id)
        session=store.get();session.touched-=2
        with self.assertRaises(ValueError):store.get(session.id)

    def test_sessions_are_separate_and_capacity_is_bounded(self):
        store=ConversationStore(capacity=2)
        a,b=store.get(),store.get();a.slots["method"]="bazi"
        self.assertNotIn("method",b.slots)
        with self.assertRaises(ValueError):store.get()


if __name__=="__main__":unittest.main()
