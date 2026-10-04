from itertools import product
import unittest

from fortune_agent.iching import build_cast
from fortune_agent.iching_reading import load_texts, select_passages, reference_hexagram


class ReadingTests(unittest.TestCase):
    def test_full_library_counts_and_special_texts(self):
        entries = load_texts()["hexagrams"]
        self.assertEqual(len(entries), 64)
        self.assertEqual(sum(len(e["lines"]) for e in entries), 384)
        self.assertEqual(sum(len(e["special"]) for e in entries), 2)
        self.assertIn("潛龍勿用", reference_hexagram(1)["lines"][0]["text"])
        self.assertIn("利永貞", reference_hexagram(2)["special"]["用六"]["text"])
        self.assertIn("未与指定纸本", reference_hexagram(52)["edition_note"])
        for entry in entries:
            self.assertIn(f"oldid={entry['source']['revision_id']}", entry["source"]["url"])
            for item in [entry["judgment"], *entry["lines"], *entry["special"].values()]:
                self.assertNotIn("{{", item["text"])
                self.assertNotIn("彖曰", item["text"])
                self.assertNotIn("象曰", item["text"])

    def test_seven_counts_choose_the_correct_kind_positions_and_priority(self):
        for count in range(7):
            cast = build_cast([9] * count + [7] * (6 - count))
            selection = select_passages(cast)
            passages = selection["passages"]
            with self.subTest(count=count):
                if count == 0:
                    self.assertEqual([(p["kind"],p["number"]) for p in passages], [("judgment",1)])
                elif count in (1, 2):
                    self.assertEqual([p["position"] for p in passages], list(range(1,count+1)))
                    self.assertTrue(passages[-1]["primary"])
                elif count == 3:
                    self.assertEqual([p["kind"] for p in passages], ["judgment", "judgment"])
                    self.assertFalse(any(p["primary"] for p in passages))
                elif count in (4, 5):
                    self.assertEqual([p["position"] for p in passages], list(range(count+1,7)))
                    self.assertTrue(passages[0]["primary"])
                    self.assertTrue(all(p["number"] == cast.changed_hexagram["number"] for p in passages))
                else:
                    self.assertEqual(passages[0]["kind"], "用九")

    def test_all_4096_casts_select_real_unique_passages_under_both_policies(self):
        counts = {0:1,1:1,2:2,3:2,4:2,5:1,6:1}
        for lines in product((6, 7, 8, 9), repeat=6):
            cast = build_cast(lines)
            for policy in ("moving-count-v1", "all-moving-v1"):
                selected = select_passages(cast, policy)["passages"]
                self.assertEqual(len(selected), len({p["id"] for p in selected}))
                self.assertTrue(all(p["source_text"] and p["source_url"] for p in selected))
                if policy == "moving-count-v1":
                    self.assertEqual(len(selected), counts[len(cast.moving_positions)])

    def test_full_change_uses_kun_special_or_general_changed_judgment(self):
        self.assertEqual(select_passages(build_cast([6]*6))["passages"][0]["kind"], "用六")
        cast = build_cast([9,6,9,6,9,6])
        selected = select_passages(cast)["passages"]
        self.assertEqual(selected[0]["kind"], "judgment")
        self.assertEqual(selected[0]["number"], cast.changed_hexagram["number"])

    def test_unknown_policy_or_reference_is_rejected(self):
        with self.assertRaises(ValueError):
            select_passages(build_cast([7]*6), "invented")
        for number in (0, 65, True):
            with self.assertRaises(ValueError):
                reference_hexagram(number)


if __name__ == "__main__":
    unittest.main()
