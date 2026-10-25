#!/usr/bin/env python3
"""Generate a self-contained rolling seven-day English study chart SVG."""

import argparse
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent


def number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite nonnegative number")
    return value


def time_label(minutes, compact=False):
    hours, mins = divmod(round(minutes), 60)
    if compact:
        return f"{hours}h{mins:02d}" if mins else f"{hours}h"
    return f"{hours}h {mins:02d}m"


def build(data):
    days = data["days"]
    if len(days) != 7:
        raise ValueError("days must contain exactly seven entries, oldest first")
    minimum = number(data.get("max_hours", 5), "max_hours")
    goal = number(data.get("daily_goal_hours", 3), "daily_goal_hours")
    opacity = number(data.get("bar_opacity", 0.75), "bar_opacity")
    if minimum <= 0 or int(minimum) != minimum or opacity > 1:
        raise ValueError("max_hours must be a positive whole number; bar_opacity must be 0–1")

    for day in days:
        if day["minutes"] is not None:
            number(day["minutes"], "minutes")
        if day["words"] is not None:
            number(day["words"], "words")

    streak = data.get("current_streak_days")
    if streak is not None:
        number(streak, "current_streak_days")
    maximum = max(int(minimum), math.ceil(goal), *(math.ceil(day["minutes"] / 60) for day in days if day["minutes"] is not None))
    complete_time = all(day["minutes"] is not None for day in days)
    complete_words = all(day["words"] is not None for day in days)
    total_minutes = sum(day["minutes"] or 0 for day in days)
    total_words = sum(day["words"] or 0 for day in days)
    study_label = time_label(total_minutes) if complete_time else "—"
    words_label = f"{total_words:g}" if complete_words else "—"
    streak_label = f"{streak:g} days" if streak is not None else "—"

    bg, fg, muted = "#0D1117", "#E6EDF3", "#B6C2D2"
    left, right, top, bottom = 38, 584, 88, 260
    height = bottom - top
    description = (
        f"Study last 7 days: {study_label}. Words last 7 days: {words_label}. "
        f"Current streak: {streak_label}. Goal: {goal:g} hours per day. "
        + "; ".join(f"{day['date']}: {time_label(day['minutes']) if day['minutes'] is not None else 'no data'}" for day in days)
    )
    s = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="300" viewBox="0 0 600 300" role="img" aria-labelledby="title desc">',
        '<title id="title">English study — last 7 days</title>',
        f'<desc id="desc">{escape(description)}</desc>',
        f'<rect x="0.5" y="0.5" width="599" height="299" rx="6" fill="{bg}" stroke="#586575" stroke-width="0.7"/>',
        '<g font-family="DejaVu Sans Mono,Consolas,monospace" font-weight="400">',
    ]

    def text(x, y, value, size=11, color=fg, anchor="middle"):
        return f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" fill="{color}" text-anchor="{anchor}">{escape(str(value))}</text>'

    for x, value, label in [(106, study_label, "Study last 7 days"), (300, words_label, "Words last 7 days"), (494, streak_label, "Current streak")]:
        s.extend([text(x, 32, value, 16), text(x, 53, label, 11, muted)])
    s.append('<path d="M202 15V61 M396 15V61" stroke="#586575" stroke-width="0.7"/>')

    for hour in range(maximum + 1):
        y = bottom - hour / maximum * height
        s.append(f'<path d="M{left} {y:.3f}H{right}" fill="none" stroke="#69788C" stroke-opacity="0.65" stroke-width="0.6" stroke-dasharray="4 3"/>')
        s.append(text(left - 7, y + 3, f"{hour}h", 10, muted, "end"))

    step = (right - left) / 7
    for i, day in enumerate(days):
        x = left + step * (i + 0.5)
        minutes = day["minutes"]
        if minutes is not None:
            bar_height = minutes / (maximum * 60) * height
            y = bottom - bar_height
            color = "#7DE39D" if minutes >= goal * 60 else "#EA6D6D"
            s.append(f'<rect x="{x - 21:.3f}" y="{y:.3f}" width="42" height="{bar_height:.3f}" fill="{color}" fill-opacity="{opacity}"><title>{escape(day["date"])}: {time_label(minutes)}</title></rect>')
            s.append(text(x, max(top - 6, y - 6), time_label(minutes, True), 9.5))
        else:
            s.append(text(x, bottom - 6, "—", 11, muted))
        s.append(text(x, 281, day["day"], 11, muted))

    goal_y = bottom - goal / maximum * height
    s.append(f'<path d="M{left} {goal_y:.3f}H{right}" stroke="{fg}" stroke-width="0.9" stroke-dasharray="5 3"/>')
    s.append(f'<path d="M{left} {top}V{bottom}H{right}" fill="none" stroke="#8B99AC" stroke-width="0.65"/>')
    s.append("</g></svg>")
    return "\n".join(s)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data.json")
    parser.add_argument("--output", type=Path, default=ROOT / "english-study-chart.svg")
    args = parser.parse_args()
    try:
        svg = build(json.loads(args.data.read_text(encoding="utf-8")))
    except (ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Invalid study data: {exc}\n")
    args.output.write_text(svg, encoding="utf-8")
    print(args.output)
