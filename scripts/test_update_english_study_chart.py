import importlib.util
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


chart = load(ROOT / "assets/english-study-chart/build_card.py", "study_chart")
updater = load(ROOT / "scripts/update-english-study-chart.py", "study_chart_updater")


class EnglishStudyChartTest(unittest.TestCase):
    def setUp(self):
        self.readme = """<!-- OPENQUIZ_STATS:START -->
Mastered: 100 words
<!-- OPENQUIZ_STREAK:12 -->

```text
📅 OpenQuiz Activity

Date        Day          Time             Words
26.10.26    Monday       0 mins           0 words
26.10.25    Sunday       5 hrs 35 mins    59 words
26.10.24    Saturday     3 hrs 59 mins    98 words
26.10.23    Friday       0 mins           —
```
<!-- OPENQUIZ_STATS:END -->"""

    def test_last_seven_days_uses_real_rows_without_inventing_history(self):
        days, streak = updater.read_days(self.readme, date(2026, 10, 26))
        self.assertEqual(len(days), 7)
        self.assertEqual(days[0], {"date": "2026-10-20", "day": "Tue", "minutes": None, "words": None})
        self.assertEqual(days[-2]["minutes"], 335)
        self.assertEqual(days[-1]["minutes"], 0)
        self.assertEqual(days[-4]["words"], None)
        self.assertEqual(streak, 12)

    def test_legacy_visible_streak_is_still_readable(self):
        readme = self.readme.replace("<!-- OPENQUIZ_STREAK:12 -->", "Streak: 12 days")
        _, streak = updater.read_days(readme, date(2026, 10, 26))
        self.assertEqual(streak, 12)

    def test_hidden_seven_days_take_priority_over_visible_four(self):
        hidden = ('<!-- OPENQUIZ_DAYS:{"2026-10-20":[87,103],'
                  '"2026-10-25":[281,59],"2026-10-26":[35,45]} -->')
        readme = self.readme.replace("<!-- OPENQUIZ_STATS:END -->", hidden + "\n<!-- OPENQUIZ_STATS:END -->")
        days, streak = updater.read_days(readme, date(2026, 10, 26))
        self.assertEqual(len(days), 7)
        self.assertEqual(days[0]["minutes"], 87)
        self.assertEqual(days[-2]["minutes"], 281)  # Visible row is 5h35, hidden is 4h41.
        self.assertEqual(days[-1]["words"], 45)
        self.assertEqual(streak, 12)

    def test_invalid_hidden_stats_do_not_fall_back_to_visible_rows(self):
        readme = self.readme.replace("<!-- OPENQUIZ_STATS:END -->",
                                     '<!-- OPENQUIZ_DAYS:{"2026-10-26":[-1,45]} -->\n<!-- OPENQUIZ_STATS:END -->')
        with self.assertRaisesRegex(ValueError, "Invalid OPENQUIZ_DAYS"):
            updater.read_days(readme, date(2026, 10, 26))

    def test_chart_expands_axis_and_marks_incomplete_totals(self):
        days, streak = updater.read_days(self.readme, date(2026, 10, 26))
        svg = chart.build({"days": days, "current_streak_days": streak})
        self.assertIn("Study last 7 days", svg)
        self.assertIn("Words last 7 days", svg)
        self.assertIn(">6h</text>", svg)
        self.assertIn("2026-10-25", svg)
        self.assertIn("Study last 7 days: —", svg)
        self.assertIn("12 days", svg)

    def test_complete_week_sums_daily_values(self):
        days, _ = updater.read_days(self.readme, date(2026, 10, 26))
        for day in days:
            if day["minutes"] is None:
                day["minutes"] = 60
            if day["words"] is None:
                day["words"] = 0
        svg = chart.build({"days": days, "current_streak_days": None})
        self.assertIn("Study last 7 days: 12h 34m", svg)
        self.assertIn("Words last 7 days: 157", svg)
        self.assertIn("Current streak: —", svg)

    def test_missing_activity_rows_fail_safely(self):
        readme = self.readme.replace("26.10.", "invalid-date.")
        with self.assertRaisesRegex(ValueError, "No parseable"):
            updater.read_days(readme, date(2026, 10, 26))

    def test_previous_recorded_days_survive_short_readme_table(self):
        previous = [{"date": "2026-10-20", "day": "Tue", "minutes": 87, "words": 103},
                    {"date": "2026-10-25", "day": "Sun", "minutes": 280, "words": 1}]
        days, _ = updater.read_days(self.readme, date(2026, 10, 26), previous)
        self.assertEqual(days[0]["minutes"], 87)
        self.assertEqual(days[-2]["minutes"], 335)  # Fresh README value wins.

    def test_readme_time_overrides_later_browser_snapshot(self):
        readme = self.readme.replace("5 hrs 35 mins", "4 hrs 41 mins")
        browser_snapshot = [{"date": "2026-10-25", "day": "Sun", "minutes": 316, "words": 59}]
        days, _ = updater.read_days(readme, date(2026, 10, 26), browser_snapshot)
        self.assertEqual(days[-2]["minutes"], 281)
        self.assertIn("4h41", chart.build({"days": days, "current_streak_days": 65}))


if __name__ == "__main__":
    unittest.main()
