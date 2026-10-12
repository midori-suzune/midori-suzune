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
CARDS = README.parent / "assets" / "anime"
USER_AGENT = "Suzune-Profile-Anime/1.0 (+https://github.com/midori-suzune/midori-suzune)"
QUERY = """
query ($name: String) {
  Page(perPage: 6) {
    mediaList(userName: $name, type: ANIME, sort: UPDATED_TIME_DESC) {
      media {
        id
        title { english romaji }
        siteUrl
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
    mask = Image.new("L", card.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 299, 419), radius=8, fill=255)
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
