"""Generate the OpenQuiz monthly history line chart for the profile README."""

from itertools import pairwise
from math import ceil, floor, log10
from xml.sax.saxutils import escape


def ticks_for(values, intervals=None):
    peak = max((value for value in values if value is not None), default=0)
    target = max(1, peak / (intervals or 4))
    magnitude = 10 ** floor(log10(target))
    step = next(factor * magnitude for factor in (1, 2, 4, 5, 10) if factor * magnitude >= target)
    intervals = intervals or max(1, ceil(peak / step))
    return range(0, intervals * step + 1, step)


def time_label(minutes):
    hours, remainder = divmod(minutes, 60)
    return f"{hours}h {remainder:02d}m" if remainder else f"{hours}h"


def draw_plot(rows, left, title, metric, ticks):
    right, top, bottom = left + 428, 54, 246
    month_inset = 30
    is_time = metric == "minutes"
    values = [row[metric] for row in rows]
    units = [value / 60 if is_time and value is not None else value for value in values]
    maximum = ticks[-1]
    svg = [
        f'<g class="{metric}">',
        f'<text class="heading" x="{(left + right) / 2:g}" y="33" text-anchor="middle">{title}</text>',
    ]
    for tick in ticks:
        y = bottom - tick / maximum * (bottom - top)
        label = f"{tick}h" if is_time else f"{tick:,}"
        svg.append(f'<path class="grid" d="M{left} {y:.2f}H{right}"/>')
        svg.append(f'<text class="tick" x="{left - 7}" y="{y + 4:.2f}" text-anchor="end">{label}</text>')
    svg.append(f'<path class="frame" d="M{left} {top}V{bottom}H{right}"/>')

    points = []
    for i, (row, value) in enumerate(zip(rows, units)):
        px = left + month_inset + i * (right - left - 2 * month_inset) / (len(rows) - 1)
        svg.append(f'<text class="axis" x="{px:.2f}" y="{bottom + 21}" text-anchor="middle">{row["name"]}</text>')
        points.append(None if value is None else (px, bottom - value / maximum * (bottom - top)))
    for previous, current in pairwise(points):
        if previous is not None and current is not None:
            svg.append(f'<path class="trend" d="M{previous[0]:.2f} {previous[1]:.2f}L{current[0]:.2f} {current[1]:.2f}"/>')
    for row, point in zip(rows, points):
        if point is None:
            continue
        label = time_label(row[metric]) if is_time else f'{row[metric]:,} words'
        source = " (sample)" if row["sample"] else ""
        svg.append(f'<circle cx="{point[0]:.2f}" cy="{point[1]:.2f}" r="3.4">'
                   f'<title>{row["name"]}: {label}{source}</title></circle>')
    svg.append("</g>")
    return svg


def build(rows):
    time_ticks = ticks_for(row["minutes"] / 60 for row in rows if row["minutes"] is not None)
    word_ticks = ticks_for((row["words"] for row in rows), intervals=len(time_ticks) - 1)
    description = []
    for row in rows:
        time = time_label(row["minutes"]) if row["minutes"] is not None else "no recorded time"
        words = f'{row["words"]:,} words' if row["words"] is not None else "no recorded words"
        source = " (sample)" if row["sample"] else ""
        description.append(f'{row["name"]}{source}: {time}, {words}')
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="290" viewBox="0 0 1120 290" role="img" aria-labelledby="title desc">',
        '<title id="title">OpenQuiz History</title>',
        f'<desc id="desc">{escape(". ".join(description))}</desc>',
        '''<style>
            .frame { fill:none; stroke:#586575; stroke-width:.75; }
            .background { fill:#0d1117; }
            .heading { fill:#e6edf3; font-size:16px; }
            .axis, .tick { fill:#b6c2d2; }
            .axis { font-size:14.5px; }
            .tick { font-size:13.25px; }
            .grid { fill:none; stroke:#69788c; stroke-opacity:.65; stroke-width:.6; stroke-dasharray:4 3; }
            .minutes { color:#7de39d; }
            .words { color:#9bb7d9; }
            .trend { fill:none; stroke:currentColor; stroke-width:1.65; stroke-linecap:round; }
            circle { fill:currentColor; stroke:#0d1117; stroke-width:1; }
        </style>''',
        '<rect class="background frame" x=".5" y=".5" width="1119" height="289" rx="6"/>',
        '<g font-family="DejaVu Sans Mono,Consolas,monospace" font-size="11">',
        '<path class="frame" d="M560 21V270"/>',
        *draw_plot(rows, 72, "Time", "minutes", time_ticks),
        *draw_plot(rows, 662, "Words", "words", word_ticks),
    ]
    return "\n".join([*svg, "</g>", "</svg>", ""])
