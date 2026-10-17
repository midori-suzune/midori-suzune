#!/usr/bin/env python3
"""Build an editable, self-contained SVG using only Python's standard library."""
import json
from pathlib import Path
from xml.sax.saxutils import escape
ROOT = Path(__file__).resolve().parent

def build(data):
    portrait = (ROOT / 'portrait.b64').read_text().strip()
    avatar = (ROOT / 'avatar.b64').read_text().strip()
    def txt(x, y, value, size=13, color='#eeeeee', weight='400'):
        return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}">{escape(str(value))}</text>'
    cells = [
        (13, 188, f"{data['vocab_streak_days']} days", 'Vocab Streak'),
        (160, 188, f"{data['mastered_words']} words", 'Mastered Word'),
        (298, 188, data['ranking'], 'Ranking'),
        (13, 245, f"{data['videos_watched']} videos", 'Watching BBC'),
        (160, 245, f"{data['articles_read']} articles", 'Reading Article'),
        (298, 245, data['latest_watching_topic'], 'Latest Watching Topic'),
    ]
    s = ['<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="426" height="286" viewBox="0 0 426 286" role="img" aria-labelledby="title desc">',
         '<title id="title">English Progress</title>',
         '<desc id="desc">English study statistics for ' + escape(str(data['name'])) + '</desc>',
         '<defs><clipPath id="card"><rect width="426" height="286" rx="11"/></clipPath><linearGradient id="fade"><stop stop-color="#050505"/><stop offset="1" stop-color="#050505" stop-opacity="0"/></linearGradient></defs>',
         '<g clip-path="url(#card)" font-family="Arial, Helvetica, sans-serif">',
         '<rect width="426" height="286" fill="#050505"/>',
         f'<image x="213" y="0" width="213" height="153" xlink:href="data:image/png;base64,{portrait}"/>',
         '<rect x="213" width="45" height="153" fill="url(#fade)"/>',
         f'<image x="13" y="16" width="17" height="20" xlink:href="data:image/png;base64,{avatar}"/>',
         txt(36,29,data['title'],13),txt(13,101,data['name'],23,'#f4f4f4','600'),
         txt(13,124,'Goal : '+str(data['goal']),14,'#bfc1cb'),
         '<path d="M0 153.5H426" stroke="#242424"/>']
    for x,y,value,label in cells:
        # Fit unusually long values without changing row/column positions.
        size = 13 if len(str(value)) <= 17 else 11
        s += [txt(x,y,value,size), txt(x,y+17,label,10.5,'#b6b9c3')]
    s += ['</g><rect x="0.5" y="0.5" width="425" height="285" rx="10.5" fill="none" stroke="#202020"/></svg>']
    return '\n'.join(s)

if __name__ == '__main__':
    data = json.loads((ROOT / 'data.json').read_text(encoding='utf-8'))
    target = ROOT / 'english-progress.svg'
    target.write_text(build(data),encoding='utf-8')
    print(target)
