import unittest

from fortune_agent.meanings import evidence_for, load_catalog
from fortune_agent.tarot import DECK, DrawnCard, Reading


def one_card(card_id, reversed_card):
    card = next(card for card in DECK if card.id == card_id)
    return Reading("测试", "single", (DrawnCard("今日提示", card, reversed_card),))


class MeaningTests(unittest.TestCase):
    def test_catalog_ids_and_coverage_are_consistent(self):
        catalog = load_catalog()
        self.assertEqual(catalog["coverage"]["card_count"], len(catalog["cards"]))
        self.assertTrue(catalog["coverage"]["complete"])
        self.assertEqual(set(catalog["cards"]), {card.id for card in DECK})
        for entry in catalog["cards"].values():
            self.assertNotIn("{{", entry["upright"])
            self.assertTrue(entry["source_url"].endswith(f"/{entry['source_page']}"))

    def test_sourced_orientation_has_page_link(self):
        evidence = evidence_for(one_card("major-15", False))[0]
        self.assertEqual(evidence["status"], "sourced")
        self.assertIn("Page:The_Pictorial_Key_to_the_Tarot.pdf/", evidence["source_url"])
        self.assertTrue(evidence["source_text"])

    def test_absent_reversed_meaning_is_not_invented(self):
        evidence = evidence_for(one_card("2-02", True))[0]
        self.assertEqual(evidence["status"], "unavailable")
        self.assertIsNone(evidence["source_text"])


if __name__ == "__main__":
    unittest.main()
