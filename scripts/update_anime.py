import html
import json
from io import BytesIO
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

from PIL import Image, ImageDraw, ImageFont, ImageOps

USER = os.environ.get("ANILIST_USER", "Suzune889")
README = Path(__file__).resolve().parent.parent / "README.md"
ASSETS = README.parent / "assets"
USER_AGENT = "Suzune-Profile-Anime/1.0 (+https://github.com/midori-suzune/midori-suzune)"
QUERY = """
query ($name: String) {
  anime: Page(perPage: 3) {
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
  manga: Page(perPage: 3) {
    mediaList(userName: $name, type: MANGA, sort: UPDATED_TIME_DESC) {
      progress
      media {
        id
        title { english romaji }
        siteUrl
        chapters
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
            "User-Agent": USER_AGENT,
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
    lists = payload["data"]
    for kind in ("anime", "manga"):
        if not isinstance(lists[kind]["mediaList"], list):
            raise RuntimeError(f"AniList did not return a {kind} list")
    return lists["anime"]["mediaList"], lists["manga"]["mediaList"]


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


def draw_progress_badge(card, progress, total, unit):
    if not isinstance(progress, int):
        return

    draw = ImageDraw.Draw(card)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    label = f"{progress}/{total}" if isinstance(total, int) and total > 0 else f"{progress} {unit}"
    text_width = draw.textlength(label, font=font)
    draw.rounded_rectangle((280 - text_width - 28, 16, 280, 54), radius=19, fill="#222e3b")
    draw.text((280 - text_width - 14, 23), label, font=font, fill="#ffffff")


def create_card(item, kind):
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
    draw_progress_badge(
        card, item.get("progress"), media.get("episodes" if kind == "anime" else "chapters"),
        "ep" if kind == "anime" else "ch",
    )
    mask = Image.new("L", card.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 299, 419), radius=16, fill=255)
    card.putalpha(mask)
    output = BytesIO()
    card.save(output, format="PNG", optimize=True)
    return output.getvalue()


def render_block(anime, manga):
    cards = []
    files = {}
    for kind, items in (("anime", anime), ("manga", manga)):
        for item in items:
            media = item["media"]
            name = f"{int(media['id'])}.png"
            files[f"{kind}/{name}"] = create_card(item, kind)
            title = html.escape(display_title(media), quote=True)
            url = html.escape(media["siteUrl"], quote=True)
            cards.append(f'<a href="{url}"><img src="assets/{kind}/{name}" width="160" alt="{kind.title()}: {title}"></a>')
    rows = ["\n".join(cards[index:index + 4]) for index in range(0, len(cards), 4)]
    content = "\n<br />\n".join(rows) if rows else "No anime or manga activity yet."
    block = ('<!--ANIME_START-->\n<p align="center">\n' + content + '\n</p>\n'
             '<p align="center">\n<!-- BEGIN YOUTUBE-CARDS -->\n'
             '<!-- END YOUTUBE-CARDS -->\n</p>\n<!--ANIME_END-->')
    return block, files


def main():
    text = README.read_text(encoding="utf-8")
    pattern = r"<!--ANIME_START-->.*?<!--ANIME_END-->"
    matches = re.findall(pattern, text, flags=re.S)
    if len(matches) != 1:
        raise RuntimeError("README must contain exactly one ANIME_START/ANIME_END block")
    youtube_pattern = r"<!-- BEGIN YOUTUBE-CARDS -->.*?<!-- END YOUTUBE-CARDS -->"
    youtube_matches = re.findall(youtube_pattern, matches[0], flags=re.S)
    if len(youtube_matches) != 1:
        raise RuntimeError("Anime block must contain exactly one YOUTUBE-CARDS block")
    block, files = render_block(*fetch_items())
    block = block.replace('<!-- BEGIN YOUTUBE-CARDS -->\n<!-- END YOUTUBE-CARDS -->', youtube_matches[0])
    for name, data in files.items():
        destination = ASSETS / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists() or destination.read_bytes() != data:
            destination.write_bytes(data)
    updated = re.sub(pattern, lambda match: block, text, flags=re.S)
    if updated != text:
        README.write_text(updated, encoding="utf-8")
    print(f"Updated anime and manga list for {USER}")


if __name__ == "__main__":
    main()
