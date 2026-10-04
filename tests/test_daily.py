import stat
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from fortune_agent.daily import daily_draw
from fortune_agent.daily_service import get_daily
from fortune_agent.daily_store import DailyStore


class FakeResponses:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            return SimpleNamespace(output=[SimpleNamespace(
                type="function_call", name="draw_tarot", arguments="{}", call_id="daily-call",
            )])
        return SimpleNamespace(output_text="这张牌提醒你安排一件可完成的小事。")


class DailyTests(unittest.TestCase):
    def test_same_profile_and_local_day_get_same_card(self):
        morning = datetime(2026, 10, 3, 1, tzinfo=timezone.utc)
        evening = datetime(2026, 10, 3, 14, tzinfo=timezone.utc)
        first = daily_draw("reader-01", "Asia/Shanghai", morning)
        second = daily_draw(" reader-01 ", "Asia/Shanghai", evening)
        self.assertEqual(first, second)
        self.assertEqual(first.day, "2026-10-03")
        self.assertEqual(len(first.reading.cards), 1)

    def test_calendar_day_uses_named_timezone(self):
        instant = datetime(2026, 10, 2, 16, 30, tzinfo=timezone.utc)
        self.assertEqual(daily_draw("reader-01", "Asia/Shanghai", instant).day, "2026-10-03")
        self.assertEqual(daily_draw("reader-01", "America/Los_Angeles", instant).day, "2026-10-02")

    def test_dst_fall_back_keeps_same_local_day_and_card(self):
        first = datetime(2026, 11, 1, 5, 30, tzinfo=timezone.utc)
        second = datetime(2026, 11, 1, 6, 30, tzinfo=timezone.utc)
        self.assertEqual(
            daily_draw("reader-01", "America/New_York", first),
            daily_draw("reader-01", "America/New_York", second),
        )

    def test_invalid_inputs_rejected(self):
        instant = datetime(2026, 10, 3, tzinfo=timezone.utc)
        for profile, zone, at in (
            (" ", "Asia/Shanghai", instant),
            ("reader", "No/Such_Zone", instant),
            ("reader", "Asia/Shanghai", datetime(2026, 10, 3)),
        ):
            with self.subTest(profile=profile, zone=zone, at=at), self.assertRaises(ValueError):
                daily_draw(profile, zone, at)

    def test_first_interpretation_is_cached_without_raw_profile(self):
        instant = datetime(2026, 10, 3, 3, tzinfo=timezone.utc)
        responses = FakeResponses()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "daily.sqlite3"
            store = DailyStore(path)
            first = get_daily(
                "private-reader", "Asia/Shanghai", store=store,
                client=SimpleNamespace(responses=responses), model="test-model",
                style="direct", at=instant,
            )
            second = get_daily(
                "private-reader", "Asia/Shanghai", store=store,
                style="gentle", at=instant,
            )
            self.assertEqual(first.reading, second.reading)
            self.assertEqual(first.interpretation, second.interpretation)
            self.assertFalse(first.cached)
            self.assertTrue(second.cached)
            self.assertEqual(second.style, "direct")
            self.assertEqual(len(responses.calls), 2)
            self.assertNotIn("private-reader", str(responses.calls))
            self.assertNotIn(b"private-reader", path.read_bytes())
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
