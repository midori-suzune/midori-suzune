#!/usr/bin/env python3
"""Refresh the English Progress card from the profile README."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARD = ROOT / "assets" / "english-progress-card"


def section(readme, name):
    match = re.search(
        rf"<!-- {name}:START -->(.*?)<!-- {name}:END -->", readme, re.DOTALL
    )
    if not match:
        raise ValueError(f"Missing {name} section in README")
    return match.group(1)


def number(text, pattern):
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        raise ValueError(f"Missing statistic matching {pattern}")
    return int(match.group(1).replace(",", ""))


def latest_watching_topic(watching):
    lines = watching.splitlines()
    header = next((line for line in lines if re.match(r"^Date\s+Topic\s+Title\s+New Vocab", line)), None)
    row = next((line for line in lines if re.match(r"^\d{2}\.\d{1,2}\.\d{1,2}\s+", line)), None)
    if not header or not row:
        raise ValueError("Missing Daily Watching header or activity")
    return row[header.index("Topic"):header.index("Title")].strip()


def read_stats(readme):
    openquiz = section(readme, "OPENQUIZ_STATS")
    rank = section(readme, "VOCAB_RANK")
    watching = section(readme, "DAILY_WATCHING")
    reading = section(readme, "DAILY_READING")
    rank_match = re.search(r"^\s*(.+?)\s+→\s+", rank, re.MULTILINE)
    if not rank_match:
        rank_match = re.search(r"^\s*(.+?)\s{2,}⣿", rank, re.MULTILINE)
    if not rank_match:
        raise ValueError("Missing vocabulary rank")
    return {
        "mastered_words": number(openquiz, r"Mastered:\s*([\d,]+)\s*words"),
        "ranking": rank_match.group(1),
        "videos_watched": number(watching, r"Daily Watching\s+([\d,]+)\s+videos"),
        "articles_read": number(reading, r"Daily Reading\s+([\d,]+)\s+articles"),
        "latest_watching_topic": latest_watching_topic(watching),
    }


def update_card():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    data_path = CARD / "data.json"
    data = json.loads(data_path.read_text(encoding="utf-8"))
    # Keep the configured streak at 50 until a reliable source is available.
    data.update(read_stats(readme))
    new_data = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if data_path.read_text(encoding="utf-8") != new_data:
        data_path.write_text(new_data, encoding="utf-8")

    sys.dont_write_bytecode = True
    sys.path.insert(0, str(CARD))
    from build_card import build

    svg_path = CARD / "english-progress.svg"
    new_svg = build(data)
    if svg_path.read_text(encoding="utf-8") != new_svg:
        svg_path.write_text(new_svg, encoding="utf-8")


if __name__ == "__main__":
    update_card()
