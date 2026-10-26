#!/usr/bin/env python3
"""Build the rolling seven-day chart from OpenQuiz's README data."""

import importlib.util
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
CHART = ROOT / "assets" / "english-study-chart"
START = "<!-- OPENQUIZ_STATS:START -->"
END = "<!-- OPENQUIZ_STATS:END -->"
ROW = re.compile(
    r"^\s*(\d{2}\.\d{2}\.\d{2})\s+\w+\s+((?:\d+\s+hrs?\s+)?\d+\s+mins)\s+(\d+\s+words|—)\s*$",
    re.MULTILINE,
)


def read_days(readme, today, previous_days=()):
    start = readme.find(START)
    end = readme.find(END, start + len(START))
    if start == -1 or end == -1:
        raise ValueError("Missing OPENQUIZ_STATS markers in README")
    section = readme[start + len(START):end]
    activity = section.split("📅 OpenQuiz Activity", 1)
    if len(activity) != 2:
        raise ValueError("Missing OpenQuiz Activity table in README")

    recorded = {}
    for match in ROW.finditer(activity[1]):
        day = datetime.strptime(match.group(1), "%y.%m.%d").date()
        duration = match.group(2)
        hours = re.search(r"(\d+)\s+hrs?", duration)
        minutes = re.search(r"(\d+)\s+mins", duration)
        words = match.group(3)
        recorded[day] = {
            "minutes": (int(hours.group(1)) * 60 if hours else 0) + int(minutes.group(1)),
            "words": int(words.split()[0]) if words != "—" else None,
        }
    if "<!-- OPENQUIZ_DAYS:" in section:
        hidden = re.search(r"<!-- OPENQUIZ_DAYS:(\{[^\n]*\})\s*-->", section)
        if not hidden:
            raise ValueError("Invalid OPENQUIZ_DAYS comment in README")
        hidden_days = json.loads(hidden.group(1))
        if not isinstance(hidden_days, dict):
            raise ValueError("OPENQUIZ_DAYS must be a date-to-stats object")
        recorded = {}
        for key, values in hidden_days.items():
            if (not isinstance(values, list) or len(values) != 2
                    or any(type(value) is not int or value < 0 for value in values)):
                raise ValueError("Invalid OPENQUIZ_DAYS daily stats")
            recorded[date.fromisoformat(key)] = {"minutes": values[0], "words": values[1]}

    if not recorded:
        raise ValueError("No parseable OpenQuiz daily activity rows in README")

    previous = {day["date"]: day for day in previous_days}
    days = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        values = recorded.get(day) or previous.get(day.isoformat()) or {"minutes": None, "words": None}
        values = {"minutes": values["minutes"], "words": values["words"]}
        days.append({"date": day.isoformat(), "day": day.strftime("%a"), **values})

    streak = re.search(r"<!-- OPENQUIZ_STREAK:\s*(\d+)\s*-->", section, re.IGNORECASE)
    if not streak:
        # Support README sections written before streak moved to an HTML comment.
        streak = re.search(r"^Streak:\s*(\d+)\s*days\s*$", section, re.MULTILINE | re.IGNORECASE)
    return days, int(streak.group(1)) if streak else None


def update_chart(today=None):
    if today is None:
        today = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    data_path = CHART / "data.json"
    data = json.loads(data_path.read_text(encoding="utf-8")) if data_path.exists() else {
        "daily_goal_hours": 3,
        "max_hours": 5,
        "bar_opacity": 0.75,
    }
    data["days"], data["current_streak_days"] = read_days(readme, today, data.get("days", ()))
    new_data = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if not data_path.exists() or data_path.read_text(encoding="utf-8") != new_data:
        data_path.write_text(new_data, encoding="utf-8")

    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("english_study_chart", CHART / "build_card.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    new_svg = module.build(data)
    svg_path = CHART / "english-study-chart.svg"
    if not svg_path.exists() or svg_path.read_text(encoding="utf-8") != new_svg:
        svg_path.write_text(new_svg, encoding="utf-8")


if __name__ == "__main__":
    update_chart()
