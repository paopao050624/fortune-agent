from collections import Counter
from itertools import product
import random
import unittest

from fortune_agent.iching import build_cast, cast_coins, load_catalog


class IChingTests(unittest.TestCase):
    def test_catalog_covers_all_64_unique_combinations_and_numbers(self):
        entries = load_catalog()["hexagrams"]
        self.assertEqual(len(entries), 64)
        self.assertEqual({item["number"] for item in entries}, set(range(1, 65)))
        self.assertEqual({item["bits_bottom_to_top"] for item in entries},
                         {"".join(bits) for bits in product("01", repeat=6)})

    def test_no_moving_lines_have_same_main_and_changed_hexagram(self):
        cast = build_cast([7] * 6)
        self.assertEqual(cast.main_hexagram["name"], "乾")
        self.assertEqual(cast.main_hexagram, cast.changed_hexagram)
        self.assertEqual(cast.moving_positions, ())

    def test_all_old_yang_changes_qian_to_kun(self):
        cast = build_cast([9] * 6)
        self.assertEqual(cast.main_hexagram["number"], 1)
        self.assertEqual(cast.changed_hexagram["number"], 2)
        self.assertEqual(cast.moving_positions, (1, 2, 3, 4, 5, 6))

    def test_lower_and_upper_trigrams_are_not_swapped(self):
        tai = build_cast([7, 7, 7, 8, 8, 8])
        pi = build_cast([8, 8, 8, 7, 7, 7])
        self.assertEqual(tai.main_hexagram["name"], "泰")
        self.assertEqual(pi.main_hexagram["name"], "否")

    def test_only_moving_position_flips(self):
        cast = build_cast([9, 7, 7, 7, 7, 7])
        self.assertEqual(cast.moving_positions, (1,))
        self.assertEqual(cast.changed_hexagram["bits_bottom_to_top"], "011111")
        self.assertEqual(cast.changed_hexagram["name"], "姤")

    def test_seeded_coin_records_are_reproducible(self):
        first = cast_coins(random.Random(42))
        self.assertEqual(first, cast_coins(random.Random(42)))
        self.assertEqual(first.lines_bottom_to_top, tuple(sum(throw) for throw in first.coins_bottom_to_top))
        self.assertTrue(all(len(throw) == 3 for throw in first.coins_bottom_to_top))
        self.assertEqual(Counter(sum(throw) for throw in product((2, 3), repeat=3)), {6: 1, 7: 3, 8: 3, 9: 1})

    def test_bad_length_value_and_boolean_are_rejected(self):
        for lines in ([7] * 5, [7] * 7, [5, 7, 7, 7, 7, 7], [True] * 6, "777777"):
            with self.subTest(lines=lines), self.assertRaises(ValueError):
                build_cast(lines)


if __name__ == "__main__":
    unittest.main()
