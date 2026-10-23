"""Render the playlist videos as portrait cards alongside AniList cards."""

import html
from html.parser import HTMLParser
from io import BytesIO
import json
import os
from pathlib import Path
import re
from urllib.parse import parse_qs, urlencode, urlparse
import urllib.request

from PIL import Image, ImageDraw, ImageFont, ImageOps


README = Path(__file__).resolve().parent.parent / "README.md"
ASSETS = README.parent / "assets" / "youtube"
START = "<!-- BEGIN YOUTUBE-CARDS -->"
END = "<!-- END YOUTUBE-CARDS -->"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


class VideoParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.videos = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            url = urlparse(attrs.get("href", ""))
            video_id = parse_qs(url.query).get("v", [""])[0]
            if url.hostname in ("www.youtube.com", "youtube.com") and re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                self.current = {"id": video_id}
        elif tag == "img" and self.current is not None:
            self.current["title"] = attrs.get("alt", "")
            self.current["duration"] = int(parse_qs(urlparse(attrs.get("src", "")).query).get("duration", [0])[0])

    def handle_endtag(self, tag):
        if tag == "a" and self.current is not None:
            if self.current.get("title"):
                self.videos.append(self.current)
            self.current = None


def get_videos(markup):
    parser = VideoParser()
    parser.feed(markup)
    if not 1 <= len(parser.videos) <= 2:
        raise ValueError("Expected one or two YouTube videos from the playlist")
    return parser.videos


def get_views(videos, api_key):
    if not api_key:
        return {}
    query = urlencode({"part": "statistics", "id": ",".join(video["id"] for video in videos)})
    request = urllib.request.Request(
        f"https://www.googleapis.com/youtube/v3/videos?{query}",
        headers={"X-goog-api-key": api_key},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if "error" in payload:
        raise RuntimeError(f"YouTube API error: {payload['error'].get('message', 'unknown error')}")
    return {item["id"]: int(item["statistics"]["viewCount"])
            for item in payload.get("items", []) if "viewCount" in item.get("statistics", {})}


def duration_label(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02}:{seconds:02}" if hours else f"{minutes}:{seconds:02}"


def title_lines(title, draw, font, max_width, max_lines=4):
    lines = []
    line = ""
    for word in title.split():
        candidate = f"{line} {word}".strip()
        if line and draw.textlength(candidate, font=font) > max_width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    visible = lines[:max_lines]
    if len(lines) > max_lines and visible:
        while visible[-1] and draw.textlength(visible[-1] + "…", font=font) > max_width:
            visible[-1] = visible[-1][:-1]
        visible[-1] += "…"
    return visible


def render_card(video, views=None):
    url = f"https://i.ytimg.com/vi/{video['id']}/mqdefault.jpg"
    with urllib.request.urlopen(url, timeout=30) as response:
        thumbnail = Image.open(BytesIO(response.read())).convert("RGB")

    card = Image.new("RGBA", (320, 448), "#1f2335")
    card.paste(ImageOps.fit(thumbnail, (320, 180), method=Image.Resampling.LANCZOS), (0, 0))
    draw = ImageDraw.Draw(card)
    if video["duration"]:
        label = duration_label(video["duration"])
        badge_font = ImageFont.truetype(FONT_BOLD, 20)
        width = draw.textlength(label, font=badge_font)
        draw.rounded_rectangle((302 - width - 18, 140, 310, 173), radius=7, fill="#111827")
        draw.text((302 - width - 9, 145), label, font=badge_font, fill="white")

    font = ImageFont.truetype(FONT_BOLD, 22)
    for index, line in enumerate(title_lines(video["title"], draw, font, 280)):
        draw.text((20, 200 + index * 32), line, font=font, fill="#e6edf3")

    small_font = ImageFont.truetype(FONT, 19)
    views_label = f"{views:,} views" if views is not None else "Watch on YouTube"
    draw.text((20, 408), views_label, font=small_font, fill="#a6adc8")

    mask = Image.new("L", card.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 319, 447), radius=16, fill=255)
    card.putalpha(mask)
    output = BytesIO()
    card.save(output, format="PNG", optimize=True)
    return output.getvalue()


def update_readme(text, videos):
    pattern = re.compile(rf"{re.escape(START)}.*?{re.escape(END)}", re.S)
    if len(pattern.findall(text)) != 1:
        raise ValueError("README must contain exactly one YOUTUBE-CARDS block")
    cards = [
        f'<a href="https://www.youtube.com/watch?v={video["id"]}">'
        f'<img src="assets/youtube/{video["id"]}.png" width="160" height="224" '
        f'alt="{html.escape(video["title"], quote=True)}"></a>'
        for video in videos
    ]
    return pattern.sub(lambda match: START + "\n" + "\n".join(cards) + "\n" + END, text)


def main():
    text = README.read_text(encoding="utf-8")
    videos = get_videos(os.environ.get("YOUTUBE_CARDS", ""))
    views = get_views(videos, os.environ.get("YOUTUBE_API_KEY"))
    updated = update_readme(text, videos)
    ASSETS.mkdir(parents=True, exist_ok=True)
    for video in videos:
        destination = ASSETS / f"{video['id']}.png"
        data = render_card(video, views.get(video["id"]))
        if not destination.exists() or destination.read_bytes() != data:
            destination.write_bytes(data)
    if updated != text:
        README.write_text(updated, encoding="utf-8")
    print(f"Updated {len(videos)} portrait YouTube cards")


if __name__ == "__main__":
    main()
