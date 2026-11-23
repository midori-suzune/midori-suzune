import importlib.util
import json
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch


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

    def test_chart_expands_axis_and_sums_recorded_days(self):
        days, streak = updater.read_days(self.readme, date(2026, 10, 26))
        svg = chart.build({"days": days, "longest_streak_days": streak})
        self.assertIn("Study last 7 days", svg)
        self.assertIn("Words last 7 days", svg)
        self.assertIn(">6h</text>", svg)
        self.assertIn("2026-10-25", svg)
        self.assertIn("Study last 7 days: 9h 34m (4 of 7 days recorded)", svg)
        self.assertIn("Words last 7 days: 157 (3 of 7 days recorded)", svg)
        self.assertIn(">Study last 7 days</text>", svg)
        self.assertIn(">Words last 7 days</text>", svg)
        self.assertIn("12 days", svg)
        self.assertIn(">Longest streak</text>", svg)

    def test_new_day_without_sync_keeps_known_totals_and_missing_column(self):
        data = {"days": [
            {"date": "2026-10-21", "day": "Wed", "minutes": 215, "words": 72},
            {"date": "2026-10-22", "day": "Thu", "minutes": 215, "words": 54},
            {"date": "2026-10-23", "day": "Fri", "minutes": 335, "words": 69},
            {"date": "2026-10-24", "day": "Sat", "minutes": 239, "words": 98},
            {"date": "2026-10-25", "day": "Sun", "minutes": 316, "words": 59},
            {"date": "2026-10-26", "day": "Mon", "minutes": 35, "words": 45},
            {"date": "2026-10-27", "day": "Tue", "minutes": None, "words": None},
        ], "longest_streak_days": 64}
        svg = chart.build(data)
        self.assertIn("Study last 7 days: 22h 35m (6 of 7 days recorded)", svg)
        self.assertIn("Words last 7 days: 397 (6 of 7 days recorded)", svg)
        self.assertIn(">Study last 7 days</text>", svg)
        self.assertIn(">—</text>", svg)

    def test_no_recorded_days_still_shows_unknown_totals(self):
        days = [{"date": "2026-10-21", "day": "Wed", "minutes": None, "words": None}] * 7
        svg = chart.build({"days": days, "longest_streak_days": None})
        self.assertIn("Study last 7 days: — (0 of 7 days recorded)", svg)
        self.assertIn("Words last 7 days: — (0 of 7 days recorded)", svg)

    def test_complete_week_sums_daily_values(self):
        days, _ = updater.read_days(self.readme, date(2026, 10, 26))
        for day in days:
            if day["minutes"] is None:
                day["minutes"] = 60
            if day["words"] is None:
                day["words"] = 0
        svg = chart.build({"days": days, "longest_streak_days": None})
        self.assertIn("Study last 7 days: 12h 34m", svg)
        self.assertIn("Words last 7 days: 157", svg)
        self.assertIn("Longest streak: —", svg)

    def test_longest_streak_survives_reset_and_increases_with_new_record(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            chart_dir = root / "assets/english-study-chart"
            chart_dir.mkdir(parents=True)
            shutil.copyfile(ROOT / "assets/english-study-chart/build_card.py", chart_dir / "build_card.py")
            data_path = chart_dir / "data.json"
            data_path.write_text(json.dumps({"current_streak_days": 71}), encoding="utf-8")
            readme_path = root / "README.md"
            with patch.object(updater, "ROOT", root), patch.object(updater, "CHART", chart_dir):
                for current, expected in ((1, 71), (72, 72), (2, 72)):
                    readme_path.write_text(
                        self.readme.replace("OPENQUIZ_STREAK:12", f"OPENQUIZ_STREAK:{current}"),
                        encoding="utf-8",
                    )
                    updater.update_chart(date(2026, 10, 26))
                    data = json.loads(data_path.read_text(encoding="utf-8"))
                    self.assertEqual(data["longest_streak_days"], expected)
                    self.assertNotIn("current_streak_days", data)
                    svg = (chart_dir / "english-study-chart.svg").read_text(encoding="utf-8")
                    self.assertIn(f"Longest streak: {expected} days", svg)

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
        self.assertIn("4h41", chart.build({"days": days, "longest_streak_days": 65}))

    def test_monthly_history_limits_calendar_months_across_year_boundary(self):
        archive = {
            "2026-09-01": [60, 1],
            "2026-10-01": [60, 2],
            "2026-11-01": [60, 3],
            "2026-12-01": [60, 4],
            "2027-01-01": [60, 5],
            "2027-02-01": [60, 6],
            "2027-03-01": [60, 7],
        }
        history = updater.render_monthly_history(archive, date(2027, 2, 1))
        rows = [line.split()[0] for line in history.splitlines() if " words" in line]
        self.assertEqual(rows, ["Jan", "Dec", "Nov", "Oct"])
        self.assertNotIn("Sep", history)
        self.assertNotIn("Feb", history)
        del archive["2026-12-01"], archive["2027-01-01"]
        history = updater.render_monthly_history(archive, date(2027, 2, 1))
        self.assertIn("Nov", history)
        self.assertNotIn("Sep", history)

    def test_history_updates_daily_samples_and_preserves_missing_metrics(self):
        archive = {"2026-10-25": [50, 1000]}
        samples = {
            date(2026, 10, 25): {"minutes": 60, "words": None},
            date(2026, 10, 26): {"minutes": 30, "words": 0},
            date(2026, 10, 27): {"minutes": 0, "words": 0},
        }
        updater.merge_history(archive, samples)
        updater.merge_history(archive, samples)
        self.assertEqual(archive, {"2026-10-25": [60, 1000], "2026-10-26": [30, 0]})
        history = updater.render_monthly_history(archive, date(2026, 11, 1))
        self.assertIn("1 hr 30 mins", history)
        self.assertIn("1,000 words", history)
        self.assertIn("Oct (2/31 days)", history)

    def test_history_update_leaves_the_activity_section_intact(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "assets").mkdir()
            readme_path = root / "README.md"
            readme_path.write_text(
                f"{self.readme}\n\n{updater.HISTORY_START}\n{updater.HISTORY_END}\n\nNext section\n",
                encoding="utf-8",
            )
            with patch.object(updater, "ROOT", root):
                updater.update_history(date(2026, 11, 1))
                updated = readme_path.read_text(encoding="utf-8")
                updater.update_history(date(2026, 11, 1))
            self.assertEqual(readme_path.read_text(encoding="utf-8"), updated)
            self.assertTrue(updated.startswith(self.readme))
            self.assertTrue(updated.endswith("\n\nNext section\n"))
            self.assertIn("🗂️ OpenQuiz History", updated)
            self.assertIn("Oct", updated)


if __name__ == "__main__":
    unittest.main()
