import json
from types import SimpleNamespace
import unittest

from fortune_agent.bazi import parse_bazi_pillars
from fortune_agent.bazi_agent import interpret_bazi
from fortune_agent.bazi_structure import analyze_structure,load_structure_rules
from fortune_agent.bazi_facts import STEMS,HIDDEN_STEMS


class StructureTests(unittest.TestCase):
    def chart(self,value="己卯 丙子 戊午 戊午"):
        return parse_bazi_pillars(value)

    def test_example_has_winter_label_roots_and_untransmitted_wealth_candidate(self):
        result=analyze_structure(self.chart())
        self.assertEqual(result["season"]["label"],"冬")
        self.assertEqual(result["season"]["relation_to_day_master"],"日主克季节五行")
        master=next(root for root in result["roots"] if root["is_day_master"])
        self.assertEqual({p["hidden_stem"] for p in master["locations"]},{"己"})
        self.assertTrue(all(p["match"]=="same_element" for p in master["locations"]))
        self.assertEqual(master["root_strength"],"unassessed")
        candidates=result["pattern_candidates"]
        self.assertEqual(len(candidates),1)
        self.assertEqual(candidates[0]["ten_god"],"正财")
        self.assertFalse(candidates[0]["transmitted"])
        self.assertEqual(result["pattern_conclusion"],"undetermined")

    def test_same_stem_and_same_element_roots_remain_distinct(self):
        result=analyze_structure(self.chart("甲子 丙寅 甲戌 乙卯"))
        master=result["roots"][2]
        self.assertEqual([(r["branch"],r["hidden_stem"],r["match"]) for r in master["locations"]],
                         [("寅","甲","same_stem"),("卯","乙","same_element")])

    def test_day_master_does_not_count_as_month_hidden_transmission(self):
        result=analyze_structure(self.chart("丙子 丙寅 甲子 丁卯"))
        hidden={item["stem"]:item for item in result["month_transmission"]}
        self.assertEqual(hidden["甲"]["visible_positions"],[])
        self.assertEqual(hidden["丙"]["visible_positions"],["年柱","月柱"])
        self.assertTrue(result["special_case_flags"])
        self.assertFalse(any(c["ten_god"]=="比肩" for c in result["pattern_candidates"]))

    def test_season_end_months_do_not_automatically_assert_earth_strength(self):
        for month in ("戊辰","己未","戊戌","己丑"):
            with self.subTest(month=month):
                result=analyze_structure(self.chart(f"甲子 {month} 戊午 戊午"))
                self.assertEqual(result["season"]["label"],"季末月")
                self.assertIsNone(result["season"]["associated_element"])
                self.assertIsNone(result["season"]["relation_to_day_master"])
                self.assertEqual(result["strength_conclusion"],"undetermined")

    def test_no_hidden_root_does_not_imply_weakness(self):
        result=analyze_structure(self.chart("甲子 乙卯 丙子 甲子"))
        self.assertEqual(result["roots"][2]["locations"],[])
        self.assertEqual(result["strength_conclusion"],"undetermined")

    def test_all_stems_and_sixty_months_keep_candidates_tied_to_actual_hidden_stems(self):
        branches="子丑寅卯辰巳午未申酉戌亥"
        for master_index,master in enumerate(STEMS):
            # Select a valid stem/branch pair for the day; a natal date is not inferred.
            day=master+branches[master_index%12]
            for i in range(60):
                month=STEMS[i%10]+branches[i%12]
                result=analyze_structure(self.chart(f"甲子 {month} {day} 丙寅"))
                with self.subTest(master=master,month=month):
                    self.assertEqual({item["stem"] for item in result["month_transmission"]},set(HIDDEN_STEMS[month[1]]))
                    self.assertTrue(all(candidate["stem"] in HIDDEN_STEMS[month[1]] for candidate in result["pattern_candidates"]))
                    self.assertTrue(all(candidate["status"]=="candidate_only" for candidate in result["pattern_candidates"]))
                    for field in ("strength_conclusion","pattern_conclusion","useful_god_conclusion"):
                        self.assertEqual(result[field],"undetermined")

    def test_inconsistent_day_master_is_rejected(self):
        chart=SimpleNamespace(year="甲子",month="丙寅",day="戊午",hour="戊午",day_master="甲")
        with self.assertRaises(ValueError):analyze_structure(chart)

    def test_model_receives_computed_structure_and_must_keep_candidate_status(self):
        class Responses:
            def create(self,**kwargs):
                self.request=kwargs
                return SimpleNamespace(output_text="正财仅为候选，不能定格。")
        responses=Responses()
        interpret_bazi(self.chart(),"看看格局候选",SimpleNamespace(responses=responses),"test-model")
        payload=json.loads(responses.request["input"][0]["content"])
        self.assertEqual(payload["structural_analysis"],analyze_structure(self.chart()))
        self.assertIn("不能仅凭透出就说成格",responses.request["instructions"])


if __name__=="__main__":unittest.main()
