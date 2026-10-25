import importlib.util
import re
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("update-english-progress.py")
SPEC = importlib.util.spec_from_file_location("update_english_progress", SCRIPT)
update_english_progress = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(update_english_progress)


class EnglishProgressStatsTest(unittest.TestCase):
    def setUp(self):
        self.readme = (SCRIPT.parent.parent / "README.md").read_text(encoding="utf-8")
        self.readme = re.sub(r"^Streak:\s*\d+\s*days\s*\n", "", self.readme, count=1, flags=re.MULTILINE)

    def with_streak(self, days):
        return re.sub(r"(Mastered:\s*\d+\s*words)", rf"\1\nStreak: {days} days", self.readme, count=1)

    def test_synced_streak_updates_card_data(self):
        stats = update_english_progress.read_stats(self.with_streak(12))
        self.assertEqual(stats["vocab_streak_days"], 12)

    def test_zero_streak_is_valid(self):
        stats = update_english_progress.read_stats(self.with_streak(0))
        self.assertEqual(stats["vocab_streak_days"], 0)

    def test_missing_streak_keeps_previous_card_data(self):
        stats = update_english_progress.read_stats(self.readme)
        self.assertNotIn("vocab_streak_days", stats)


if __name__ == "__main__":
    unittest.main()
