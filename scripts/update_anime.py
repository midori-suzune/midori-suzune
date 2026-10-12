import html
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

USER = os.environ.get("ANILIST_USER", "Suzune889")
README = Path(__file__).resolve().parent.parent / "README.md"
QUERY = """
query ($name: String) {
  Page(perPage: 6) {
    mediaList(userName: $name, type: ANIME, sort: UPDATED_TIME_DESC) {
      progress
      media {
        title { romaji }
        siteUrl
        coverImage { large }
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


def render_block(items):
    cells = []
    for item in items:
        media = item["media"]
        title = html.escape(media["title"]["romaji"], quote=True)
        url = html.escape(media["siteUrl"], quote=True)
        cover = html.escape(media["coverImage"]["large"], quote=True)
        cells.append(
            f'<a href="{url}"><img src="{cover}" width="110" '
            f'title="{title} - tập {int(item["progress"])}" alt="{title}"></a>'
        )
    content = "\n".join(cells) if cells else "No anime activity yet."
    return '<!--ANIME_START-->\n<p align="center">\n' + content + '\n</p>\n<!--ANIME_END-->'


def main():
    text = README.read_text(encoding="utf-8")
    pattern = r"<!--ANIME_START-->.*?<!--ANIME_END-->"
    if len(re.findall(pattern, text, flags=re.S)) != 1:
        raise RuntimeError("README must contain exactly one ANIME_START/ANIME_END block")
    block = render_block(fetch_items())
    updated = re.sub(pattern, lambda match: block, text, flags=re.S)
    if updated != text:
        README.write_text(updated, encoding="utf-8")
    print(f"Updated anime list for {USER}")


if __name__ == "__main__":
    main()
