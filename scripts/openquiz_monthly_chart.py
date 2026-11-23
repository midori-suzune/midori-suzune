"""Generate the OpenQuiz monthly history line chart for the profile README."""

from itertools import pairwise
from math import ceil, floor, log10
from xml.sax.saxutils import escape


def ticks_for(values):
    peak = max((value for value in values if value is not None), default=0)
    target = max(1, peak / 4)
    magnitude = 10 ** floor(log10(target))
    step = next(factor * magnitude for factor in (1, 2, 4, 5, 10) if factor * magnitude >= target)
    return range(0, max(1, ceil(peak / step)) * step + 1, step)


def time_label(minutes):
    hours, remainder = divmod(minutes, 60)
    return f"{hours}h {remainder:02d}m" if remainder else f"{hours}h"


def draw_plot(rows, x, title, metric):
    left, right, top, bottom = x + 44, x + 300, 78, 175
    is_time = metric == "minutes"
    values = [row[metric] for row in rows]
    units = [value / 60 if is_time and value is not None else value for value in values]
    ticks = ticks_for(units)
    maximum = ticks[-1]
    svg = [f'<text x="{x}" y="56">{title}</text>']
    for tick in ticks:
        y = bottom - tick / maximum * (bottom - top)
        label = f"{tick}h" if is_time else f"{tick:,}"
        svg.append(f'<path class="grid" d="M{left} {y:.2f}H{right}"/>')
        svg.append(f'<text class="axis" x="{left - 7}" y="{y + 4:.2f}" text-anchor="end">{label}</text>')

    points = []
    for i, (row, value) in enumerate(zip(rows, units)):
        px = left + (i + 0.5) * (right - left) / len(rows)
        svg.append(f'<text class="axis" x="{px:.2f}" y="193" text-anchor="middle">{row["name"]}</text>')
        points.append(None if value is None else (px, bottom - value / maximum * (bottom - top)))
    for previous, current in pairwise(points):
        if previous is not None and current is not None:
            svg.append(f'<path class="trend" d="M{previous[0]:.2f} {previous[1]:.2f}L{current[0]:.2f} {current[1]:.2f}"/>')
    for row, point in zip(rows, points):
        if point is None:
            continue
        label = time_label(row[metric]) if is_time else f'{row[metric]:,} words'
        source = " (sample)" if row["sample"] else ""
        kind = "sample" if row["sample"] else "actual"
        svg.append(f'<circle class="{kind}" cx="{point[0]:.2f}" cy="{point[1]:.2f}" r="3.6">'
                   f'<title>{row["name"]}: {label}{source}</title></circle>')
    return svg


def build(rows):
    description = []
    for row in rows:
        time = time_label(row["minutes"]) if row["minutes"] is not None else "no recorded time"
        words = f'{row["words"]:,} words' if row["words"] is not None else "no recorded words"
        source = " (sample)" if row["sample"] else ""
        description.append(f'{row["name"]}{source}: {time}, {words}')
    height = 212
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="{height}" viewBox="0 0 640 {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">OpenQuiz History</title>',
        f'<desc id="desc">{escape(". ".join(description))}</desc>',
        '''<style>
            svg { --bg:#f6f8fa; --fg:#1f2328; --muted:#59636e; --grid:#d1d9e0; }
            @media (prefers-color-scheme: dark) {
                svg { --bg:#151b23; --fg:#f0f6fc; --muted:#9198a1; --grid:#3d444d; }
            }
            text { fill:var(--fg); }
            .background { fill:var(--bg); }
            .axis { fill:var(--muted); font-size:10px; }
            .grid { stroke:var(--grid); }
            .trend { fill:none; stroke:var(--fg); stroke-width:1.6; }
            .sample { fill:var(--bg); stroke:var(--fg); stroke-width:1.4; }
            .actual { fill:var(--fg); }
        </style>''',
        f'<rect class="background" width="640" height="{height}" rx="6"/>',
        '<g font-family="DejaVu Sans Mono,Consolas,monospace" font-size="12">',
        '<text x="16" y="28">🗂️ OpenQuiz History</text>',
        *draw_plot(rows, 16, "Time", "minutes"),
        *draw_plot(rows, 324, "Words", "words"),
    ]
    return "\n".join([*svg, "</g>", "</svg>", ""])
