import html
import json
from io import BytesIO
import math
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

from PIL import Image, ImageDraw, ImageFont, ImageOps

USER = os.environ.get("ANILIST_USER", "Suzune889")
README = Path(__file__).resolve().parent.parent / "README.md"
CARDS = README.parent / "assets" / "anime"
USER_AGENT = "Suzune-Profile-Anime/1.0 (+https://github.com/midori-suzune/midori-suzune)"
QUERY = """
query ($name: String) {
  Page(perPage: 6) {
    mediaList(userName: $name, type: ANIME, sort: UPDATED_TIME_DESC) {
      progress
      media {
        id
        title { english romaji }
        siteUrl
        episodes
        coverImage { extraLarge }
      }
    }
  }
}
"""


def fetch_items():
    request = urllib.request.Request(
        "https://graphql.anilist.co",
        data=json.dumps({"query": QUERY, "variables": {"name": USER}}).encode(),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": (
                "Suzune-Profile-Anime/1.0 "
                "(+https://github.com/midori-suzune/midori-suzune)"
            ),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read(2000).decode("utf-8", errors="replace")
        raise RuntimeError(f"AniList HTTP {error.code}: {detail}") from error
    if payload.get("errors"):
        raise RuntimeError("AniList API error: " + json.dumps(payload["errors"]))
    items = payload["data"]["Page"]["mediaList"]
    if not isinstance(items, list):
        raise RuntimeError("AniList did not return an anime list")
    return items


def title_lines(title, draw, font, width):
    lines = []
    current = ""
    for word in title.split():
        candidate = f"{current} {word}".strip()
        if current and draw.textlength(candidate, font=font) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    visible = lines[:2]
    if len(lines) > 2:
        visible[-1] += "..."
    for index, line in enumerate(visible):
        if draw.textlength(line, font=font) > width:
            while line and draw.textlength(line + "...", font=font) > width:
                line = line[:-1]
            visible[index] = line + "..."
    return visible


def display_title(media):
    return media["title"].get("english") or media["title"]["romaji"]


def draw_progress_border(card, progress, episodes):
    if not isinstance(progress, int) or not isinstance(episodes, int) or episodes <= 0:
        return

    # Trace the rounded border clockwise from the top-left corner.
    left, top, right, bottom, radius = 6, 6, 293, 413, 12
    points = [(left + radius, top), (right - radius, top)]
    corners = (
        (right - radius, top + radius, -90, 0),
        (right - radius, bottom - radius, 0, 90),
        (left + radius, bottom - radius, 90, 180),
        (left + radius, top + radius, 180, 270),
    )
    for cx, cy, start, end in corners:
        for angle in range(start, end + 1, 3):
            radians = math.radians(angle)
            points.append((cx + radius * math.cos(radians), cy + radius * math.sin(radians)))
        if start == -90:
            points.append((right, bottom - radius))
        elif start == 0:
            points.append((left + radius, bottom))
        elif start == 90:
            points.append((left, top + radius))

    draw = ImageDraw.Draw(card)
    draw.line(points, fill="#56606b", width=8, joint="curve")
    remaining = min(max(progress / episodes, 0), 1) * sum(
        math.dist(a, b) for a, b in zip(points, points[1:])
    )
    completed = [points[0]]
    for start, end in zip(points, points[1:]):
        length = math.dist(start, end)
        if remaining < length:
            completed.append(tuple(a + (b - a) * remaining / length for a, b in zip(start, end)))
            break
        completed.append(end)
        remaining -= length
    if len(completed) > 1:
        draw.line(completed, fill="#ff9b54", width=8, joint="curve")

    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    label = f"{progress}/{episodes}"
    text_width = draw.textlength(label, font=font)
    draw.rounded_rectangle((280 - text_width - 28, 16, 280, 54), radius=19, fill="#222e3b")
    draw.text((280 - text_width - 14, 23), label, font=font, fill="#ffffff")


def create_card(item):
    media = item["media"]
    request = urllib.request.Request(
        media["coverImage"]["extraLarge"], headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        source = Image.open(BytesIO(response.read())).convert("RGBA")
    # Render at twice the display size so text stays sharp on dense screens.
    card = ImageOps.fit(source, (300, 420), method=Image.Resampling.LANCZOS)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    lines = title_lines(display_title(media), ImageDraw.Draw(card), font, 252)
    overlay_height = 28 + len(lines) * 32
    overlay_top = 420 - overlay_height
    overlay = Image.new("RGBA", card.size, (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rectangle(
        (0, overlay_top, 300, 420), fill=(13, 17, 23, 195)
    )
    card = Image.alpha_composite(card, overlay)
    draw = ImageDraw.Draw(card)
    for index, line in enumerate(lines):
        draw.text((24, overlay_top + 12 + index * 32), line, font=font, fill="#e6edf3")
    draw_progress_border(card, item.get("progress"), media.get("episodes"))
    mask = Image.new("L", card.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 299, 419), radius=16, fill=255)
    card.putalpha(mask)
    output = BytesIO()
    card.save(output, format="PNG", optimize=True)
    return output.getvalue()


def render_block(items):
    cards = []
    files = {}
    for item in items:
        media = item["media"]
        name = f"{int(media['id'])}.png"
        files[name] = create_card(item)
        title = html.escape(display_title(media), quote=True)
        url = html.escape(media["siteUrl"], quote=True)
        cards.append(f'<a href="{url}"><img src="assets/anime/{name}" width="150" alt="{title}"></a>')
    rows = ["\n".join(cards[index:index + 3]) for index in range(0, len(cards), 3)]
    content = "\n<br />\n".join(rows) if rows else "No anime activity yet."
    block = '<!--ANIME_START-->\n<p align="center">\n' + content + '\n</p>\n<!--ANIME_END-->'
    return block, files


def main():
    text = README.read_text(encoding="utf-8")
    pattern = r"<!--ANIME_START-->.*?<!--ANIME_END-->"
    if len(re.findall(pattern, text, flags=re.S)) != 1:
        raise RuntimeError("README must contain exactly one ANIME_START/ANIME_END block")
    block, files = render_block(fetch_items())
    CARDS.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        destination = CARDS / name
        if not destination.exists() or destination.read_bytes() != data:
            destination.write_bytes(data)
    updated = re.sub(pattern, lambda match: block, text, flags=re.S)
    if updated != text:
        README.write_text(updated, encoding="utf-8")
    print(f"Updated anime list for {USER}")


if __name__ == "__main__":
    main()
