"""Block diagram of the surf generator -> hardware/docs/blocks.svg (also embedded in the app)."""
import html, os
W, H = 1180, 520
INK, SOFT, ACC, BG = '#2b3033', '#6d7377', '#00a79b', '#fbfbf8'
items = []
def box(x, y, w, h, title, sub='', hl=False):
    items.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="{"#e6f7f5" if hl else "#fff"}" stroke="{ACC if hl else INK}" stroke-width="{1.6 if hl else 1.2}"/>')
    items.append(f'<text x="{x+w/2}" y="{y+h/2-(4 if sub else -4)}" text-anchor="middle" font-size="13" font-weight="700" fill="{INK}">{html.escape(title)}</text>')
    if sub: items.append(f'<text x="{x+w/2}" y="{y+h/2+13}" text-anchor="middle" font-size="10.5" fill="{SOFT}">{html.escape(sub)}</text>')
def arrow(pts, label='', ctrl=False, lx=None, ly=None):
    col = ACC if ctrl else INK
    d = ' '.join(f'{x},{y}' for x, y in pts)
    dash = 'stroke-dasharray="5 3"' if ctrl else ''
    mk = 'ac' if ctrl else 'a'
    items.append(f'<polyline points="{d}" fill="none" stroke="{col}" stroke-width="1.4" {dash} marker-end="url(#{mk})"/>')
    if label:
        x, y = (lx, ly) if lx is not None else ((pts[0][0] + pts[-1][0]) / 2, min(p[1] for p in pts) - 6)
        items.append(f'<text x="{x}" y="{y}" text-anchor="middle" font-size="10.5" fill="{col}" font-weight="600">{html.escape(label)}</text>')
# audio chain (top row)
box(20, 40, 120, 56, 'Шум', 'Q1 → U1A', True)
box(190, 40, 130, 56, 'Розовый фильтр', 'R9–R12, C9–C11, U1B')
box(370, 40, 120, 56, 'ФНЧ волны', 'U6A (срез ∝ Iabc)')
box(540, 40, 120, 56, 'Усилитель', 'U6B (∝ Iabc)')
box(710, 40, 110, 56, 'Смеситель', 'U2A')
box(870, 40, 100, 56, 'Volume', 'RV4')
box(1010, 40, 160, 56, 'Усилитель мощности', 'LM386 → динамик')
arrow([(140, 68), (190, 68)], 'W'); arrow([(320, 68), (370, 68)], 'PN'); arrow([(490, 68), (540, 68)])
arrow([(660, 68), (710, 68)]); arrow([(820, 68), (870, 68)]); arrow([(970, 68), (1010, 68)])
# foam
box(370, 150, 120, 56, 'Фильтр верхних', 'C17, R23')
box(540, 150, 120, 56, 'Усилитель пены', 'U7A (∝ Iabc)')
arrow([(80, 96), (80, 178), (370, 178)], 'W', lx=225, ly=170)
arrow([(490, 178), (540, 178)]); arrow([(660, 178), (685, 178), (685, 80), (710, 80)])
# control
box(20, 300, 140, 56, 'Компаратор', 'U4A: шум > порог Surf', True)
box(210, 300, 120, 56, 'Триггеры', 'U5: бит по фронту часов')
box(210, 400, 120, 56, 'Часы Tide', 'U3A, U3B, RV6')
box(380, 300, 110, 56, 'Вентили И', 'U9: часы × бит')
box(540, 300, 120, 56, 'Огибающая', 'R, D6, C26 → U3C')
box(710, 300, 120, 56, 'Задержка', 'R47, C27 → U3D')
arrow([(80, 96), (80, 300)], '', False)
items.append(f'<text x="92" y="250" font-size="10.5" fill="{INK}">W</text>')
arrow([(160, 328), (210, 328)], 'бит'); arrow([(270, 400), (270, 356)], 'CK1, CK2', ctrl=True, lx=312, ly=382)
arrow([(330, 328), (380, 328)]); arrow([(330, 428), (435, 428), (435, 356)], '', ctrl=True)
arrow([(490, 328), (540, 328)]); arrow([(660, 328), (710, 328)], 'VW', lx=685, ly=320)
arrow([(600, 300), (600, 270), (430, 270), (430, 96)], 'VW → Iabc', ctrl=True, lx=520, ly=262)
arrow([(620, 300), (620, 285), (600, 285), (600, 96)], '', ctrl=True)
arrow([(770, 300), (770, 230), (600, 230), (600, 206)], 'FW', ctrl=True, lx=700, ly=224)
# knobs
box(880, 190, 120, 40, 'Tone', 'RV3 → Iabc U6A', False)
arrow([(940, 190), (940, 150), (430, 150), (430, 96)], '', ctrl=True)
box(880, 300, 120, 40, 'Surf', 'RV5 → порог', False)
arrow([(880, 320), (160, 320)] if False else [(880, 320), (850, 320), (850, 270), (110, 270), (110, 300)], '', ctrl=True)
box(880, 400, 120, 40, 'LED волны', 'Q2 → D10', False)
arrow([(830, 330), (850, 330), (850, 420), (880, 420)], '', ctrl=True)
items.append(f'<g font-size="10.5" fill="{SOFT}"><text x="780" y="490">сплошная линия — звук</text><text x="780" y="506" fill="{ACC}">пунктир — управляющее напряжение и токи Iabc</text></g>')
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Helvetica, Arial, sans-serif">'
       f'<defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="{INK}"/></marker>'
       f'<marker id="ac" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="{ACC}"/></marker></defs>'
       f'<rect width="{W}" height="{H}" fill="{BG}"/>' + ''.join(items) + '</svg>')
out = os.path.join(os.path.dirname(__file__), '..', 'docs', 'blocks.svg')
open(out, 'w').write(svg)
print('ok')
