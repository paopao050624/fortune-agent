import random
import unittest

from fortune_agent.tarot import DECK, draw_reading


class TarotTests(unittest.TestCase):
    def test_deck_has_78_unique_cards(self):
        self.assertEqual(len(DECK), 78)
        self.assertEqual(len({card.id for card in DECK}), 78)

    def test_seeded_draw_is_reproducible(self):
        first = draw_reading("今天适合做什么？", "three", rng=random.Random(42))
        second = draw_reading("今天适合做什么？", "three", rng=random.Random(42))
        self.assertEqual(first, second)
        self.assertEqual(len({item.card.id for item in first.cards}), 3)
        self.assertEqual([item.position for item in first.cards], ["现状", "影响", "建议"])

    def test_user_can_select_distinct_slots(self):
        reading = draw_reading("学习", "three", (1, 15, 78), random.Random(7))
        self.assertEqual(len(reading.cards), 3)
        self.assertEqual(len({item.card.id for item in reading.cards}), 3)

    def test_invalid_selections_are_rejected(self):
        for picks in ((1, 1, 2), (0, 2, 3), (1, 2), (1, 2, 79)):
            with self.subTest(picks=picks), self.assertRaises(ValueError):
                draw_reading("学习", "three", picks)

    def test_question_is_required(self):
        with self.assertRaises(ValueError):
            draw_reading("  ")


if __name__ == "__main__":
    unittest.main()
