import unittest
from copy import deepcopy
from types import SimpleNamespace

from fortune_agent.bazi_rules import load_rule_catalog, validate_rule_catalog, wealth_checklist
from fortune_agent.bazi_sources import load_ziping_catalog


class WealthChecklistTests(unittest.TestCase):
    def test_visible_resource_does_not_confirm_pattern(self):
        chart = SimpleNamespace(year="己卯", month="丙子", day="戊午", hour="戊午", day_master="戊")
        checklist = wealth_checklist(chart)
        self.assertTrue(checklist["observations"]["resource_visible"]["present"])
        self.assertEqual(checklist["month_wealth_hidden_stems"][0]["stem"], "癸")
        self.assertEqual(checklist["conclusion"], "undetermined")
        self.assertIn("位置妥适", checklist["paths"][2]["unverified_conditions"])

    def test_day_master_itself_is_not_a_visible_peer_observation(self):
        chart = SimpleNamespace(year="甲寅", month="乙卯", day="戊午", hour="丙寅", day_master="戊")
        checklist = wealth_checklist(chart)
        self.assertFalse(checklist["observations"]["peer_visible"]["present"])
        self.assertEqual(checklist["conclusion"], "undetermined")

    def test_hidden_stems_are_not_counted_as_visible_stems(self):
        chart = SimpleNamespace(year="甲寅", month="乙卯", day="戊午", hour="甲寅", day_master="戊")
        checklist = wealth_checklist(chart)
        self.assertFalse(checklist["observations"]["resource_visible"]["present"])
        self.assertEqual(checklist["month_wealth_hidden_stems"], [])

    def test_rules_reference_the_scan_verified_financial_conditions(self):
        catalog = load_rule_catalog()
        source = next(entry for entry in load_ziping_catalog()["entries"] if entry["id"] == catalog["source_id"])
        self.assertEqual(source["printed_pages"], [19])
        self.assertEqual(source["scan_pages"], [28])
        self.assertEqual(len(catalog["paths"]), 3)
        for path in catalog["paths"]:
            self.assertTrue(path["unverified_conditions"])

    def test_missing_condition_or_duplicate_path_is_rejected(self):
        source_entries = load_ziping_catalog()["entries"]
        catalog = deepcopy(load_rule_catalog())
        catalog["paths"][2]["unverified_conditions"].remove("两不相克")
        with self.assertRaisesRegex(ValueError, "待核实条件"):
            validate_rule_catalog(catalog, source_entries)
        catalog = deepcopy(load_rule_catalog())
        catalog["paths"][2] = deepcopy(catalog["paths"][0])
        with self.assertRaisesRegex(ValueError, "唯一"):
            validate_rule_catalog(catalog, source_entries)

    def test_changed_source_page_or_wording_is_rejected(self):
        entries = deepcopy(load_ziping_catalog()["entries"])
        source = next(entry for entry in entries if entry["id"] == load_rule_catalog()["source_id"])
        source["source_text"] = source["source_text"].replace("兩不相剋", "无需条件")
        with self.assertRaisesRegex(ValueError, "原文不匹配"):
            validate_rule_catalog(load_rule_catalog(), entries)
        source["scan_pages"] = [19]
        with self.assertRaisesRegex(ValueError, "页码"):
            validate_rule_catalog(load_rule_catalog(), entries)

    def test_unknown_observation_group_is_rejected(self):
        catalog = deepcopy(load_rule_catalog())
        catalog["paths"][0]["observation_groups"].append("strength_confirmed")
        with self.assertRaisesRegex(ValueError, "观察字段"):
            validate_rule_catalog(catalog, load_ziping_catalog()["entries"])


if __name__ == "__main__":
    unittest.main()
