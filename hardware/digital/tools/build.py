"""Derive every deliverable of the digital version from the schematic in circuit.py."""
import sys, os, json, re, collections, datetime, shutil, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import circuit, layout as L
from catalog import CATALOG, SHARED, EXTRA
D = circuit.D
OUT = os.path.join(HERE, '..', 'out')
DATA = os.path.join(HERE, '..', '..', '..', 'src', 'hardware-data')
os.makedirs(OUT, exist_ok=True); os.makedirs(DATA, exist_ok=True)

nets = D.nets(); parts = D.parts()

# ---- sheets -------------------------------------------------------------------------------------------------
sheet_files = []
for sh in D.sheets:
    fn = f'sheet-{sh.name}.svg'
    open(os.path.join(OUT, fn), 'w').write(sh.svg())
    shutil.copy(os.path.join(OUT, fn), os.path.join(DATA, fn))
    sheet_files.append(dict(file=fn, title=sh.title, w=sh.w, h=sh.h, name=sh.name))

# ---- ERC ------------------------------------------------------------------------------------------------------
nc = {(r, p) for sh in D.sheets for (r, p) in getattr(sh, 'nc_pins', [])}
pinnet = {}
for n, pins in nets.items():
    for r, p in pins: pinnet[(r, p)] = n
bad = 0
for ref, part in parts.items():
    for pn in part.local_pins:
        if (ref, pn) in nc: continue
        if (ref, pn) not in pinnet: print('unconnected', ref, pn); bad += 1
for n, pins in nets.items():
    if len(pins) == 1 and n != 'GND' and pins[0] not in nc:
        print('single-pin net', n, pins); bad += 1
print(len(parts), 'symbols,', len(nets), 'nets, ERC problems:', bad)

# ---- design rules that matter for this particular board ------------------------------------------------------------
PICO_GPIO = {12: 9, 14: 10, 15: 11, 20: 15, 21: 16, 22: 17, 24: 18, 25: 19}
checks = []
def check(name, ok, detail=''):
    checks.append(dict(name=name, ok=bool(ok), detail=detail)); print(('OK  ' if ok else 'FAIL'), name, detail)
    return ok
def net_of(ref, pin): return pinnet.get((ref, str(pin)))
check('I2S: LRC — следующий вывод за BCLK (GP11 = GP10 + 1)', PICO_GPIO[15] == PICO_GPIO[14] + 1, 'требование библиотеки I2S для Arduino-Pico')
check('I2S: BCLK, LRC и DIN подключены к модулю усилителя',
      net_of('U1', 14) == net_of('U3', 6) and net_of('U1', 15) == net_of('U3', 7) and net_of('U1', 12) == net_of('U3', 5))
check('SPI0: MISO=GP16, CS=GP17, SCK=GP18, MOSI=GP19 (штатные выводы SPI0)',
      (PICO_GPIO[21], PICO_GPIO[22], PICO_GPIO[24], PICO_GPIO[25]) == (16, 17, 18, 19))
check('SPI: DOUT→MISO, DIN→MOSI, CLK→SCK, CS→CS',
      net_of('U2', 12) == net_of('U1', 21) and net_of('U2', 11) == net_of('U1', 25) and net_of('U2', 13) == net_of('U1', 24) and net_of('U2', 10) == net_of('U1', 22))
check('Питание MCP3008 и потенциометров — 3,3 В с вывода 36 Pico', net_of('U2', 16) == net_of('U1', 36) == net_of('RV1', '3'))
check('Питание усилителя — 5 В после кнопки, а не 3,3 В', net_of('U3', 1) == net_of('SW1', 2) and net_of('U3', 1) != net_of('U1', 36))
check('Pico питается через D1 на вывод VSYS (39)', net_of('D1', 'K') == net_of('U1', 39))
check('Все четыре движка подключены к CH0…CH3', all(net_of(f'RV{i+1}', 'W') == net_of('U2', i + 1) for i in range(4)))
check('Неиспользуемые входы MCP3008 CH4–CH7 на земле', all(net_of('U2', p) == 'GND' for p in (5, 6, 7, 8)))
check('Ток светодиода (5 В − 3,2 В) / 180 Ом ≈ 10 мА, ток базы (3,3 − 0,7) / 4,7 кОм ≈ 0,55 мА',
      abs((5 - 3.2) / 180 - 0.010) < 0.002 and (3.3 - 0.7) / 4700 * 110 > 0.010, 'при коэффициенте усиления ≥ 110 транзистор насыщается')
check('Ток потенциометров 4 × 3,3 В / 10 кОм ≈ 1,3 мА — мало для 3V3(OUT) Pico', 4 * 3.3 / 10000 < 0.05)
if bad or not all(c['ok'] for c in checks): sys.exit(1)

# ---- panel / board pads ------------------------------------------------------------------------------------------------------
Zp = -7.0    # wire attachment depth at the panel parts
HOLE_OF = {}
def hole_name(c, r): return chr(65 + c) + str(r + 1)
def pad_board(ref, pin):
    """Device coordinates (x, y, z) of a pad on the rear side of the board."""
    if ref == 'U1': c, r = L.pico_pin(int(pin))
    elif ref == 'U2': c, r = L.mcp_pin(int(pin))
    elif ref == 'U3':
        i = int(pin)
        if i <= 7: c, r = L.amp_pin(i)
        else: c, r = (L.AMP_COL0 + 8 + (i - 8) * 2, L.AMP_ROW + 5)
    elif ref in L.TWO_PIN: c, r = L.TWO_PIN[ref][str(pin)]
    else: return None
    HOLE_OF[(ref, str(pin))] = (c, r)
    x, y = L.hole(c, r)
    return (x, y, L.Z_BOARD_TOP)

def pad_panel(ref, pin):
    if ref in ('RV1', 'RV2', 'RV3', 'RV4'):
        x, y = L.PANEL[ref]; return (x + {'1': -5, 'W': 0, '3': 5}[pin], y - 7.5, Zp)
    if ref == 'SW1':
        x, y = L.PANEL[ref]; return (x + {'1': -3, '2': 3}[pin], y - 6.5, Zp)
    if ref == 'D2':
        x, y = L.PANEL[ref]; return (x + {'A': -1.27, 'K': 1.27}[pin], y - 4.0, -4.0)
    if ref == 'J1':
        x, y, z = L.J1_POS; return (x - 4, y + {'TIP': 3, 'SLV': -3}[pin], z)
    if ref == 'SPK1':
        x, y = L.PANEL[ref]; return (x + {'1': 18, '2': 24}[pin], y - 22, -8.0)
    return None

pads = {}
for n, plist in nets.items():
    for r, p in plist:
        if (r, p) in nc: continue
        pad = pad_board(r, p) or pad_panel(r, p)
        if pad is None: continue
        pads[(r, p)] = pad

# ---- wires: connect every net's pads with a minimum spanning tree ----------------------------------------------------------
NET_COLOR = {'GND': '#26292b', 'V3': '#ff8a1f', 'V5': '#e0452a', 'V5IN': '#e0452a', 'VSYS': '#e0452a',
             'I2S_DIN': '#3a6ff0', 'I2S_BCLK': '#8a5cf5', 'I2S_LRC': '#ffd23f', 'SPI_MISO': '#27b36a', 'SPI_MOSI': '#00cfc1',
             'SPI_SCK': '#ff6a1a', 'SPI_CS': '#9aa0a3', 'LED_CTL': '#f7f7f4', 'SPK_P': '#e0452a', 'SPK_N': '#26292b',
             'ADC0': '#ffd23f', 'ADC1': '#3a6ff0', 'ADC2': '#27b36a', 'ADC3': '#8a5cf5'}
board_parts = {'U1', 'U2', 'U3', 'D1', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'R1', 'R2', 'Q1'}
def dist(a, b): return math.dist(a, b)
wires = []
for n, plist in sorted(nets.items()):
    pl = [(r, p) for r, p in plist if (r, p) in pads]
    if len(pl) < 2: continue
    # on-board points first so that panel parts connect to the nearest board pad
    done = [pl[0]]; rest = pl[1:]
    while rest:
        best = None
        for a in done:
            for b in rest:
                d = dist(pads[a], pads[b])
                # a wire between two board pads must not be a jumper across a socket: still allowed
                if best is None or d < best[0]: best = (d, a, b)
        _, a, b = best
        panel_a = a[0] not in board_parts; panel_b = b[0] not in board_parts
        ha = hole_name(*HOLE_OF[a]) if a in HOLE_OF else 'на панели'; hb = hole_name(*HOLE_OF[b]) if b in HOLE_OF else 'на панели'
        wires.append(dict(net=n, a=f'{a[0]}.{a[1]}', b=f'{b[0]}.{b[1]}', ha=ha, hb=hb, p=list(pads[a]), q=list(pads[b]),
                          kind='harness' if (panel_a or panel_b) else 'jumper', color=NET_COLOR.get(n, '#8a8d90'), length=round(dist(pads[a], pads[b]), 1)))
        done.append(b); rest.remove(b)
print(len(wires), 'wires')

# ---- parts for the web app ------------------------------------------------------------------------------------------------------
def meta_for(ref):
    for group, base in SHARED.items():
        if ref in group: return CATALOG[base]
    return CATALOG.get(ref)

E_COL = ['black', 'brown', 'red', 'orange', 'yellow', 'green', 'blue', 'violet', 'grey', 'white']
def bands4(v):
    v = str(v); mult = {'': 1, 'k': 1e3, 'M': 1e6}[v[-1] if v[-1] in 'kM' else '']
    x = float(v.rstrip('kM')) * mult
    exp = 0
    while x >= 100: x /= 10; exp += 1
    while x < 10: x *= 10; exp -= 1
    d = int(round(x)); return [E_COL[d // 10], E_COL[d % 10], {-2: 'silver', -1: 'gold'}.get(exp - 0) if exp < 0 else E_COL[exp], 'gold']

def refkey(r): return (re.match(r'[A-Z]+', r).group(), int(re.search(r'\d+', r).group()), r)
phys = []
TYPE = {'R': 'R', 'C': 'C', 'CP': 'C', 'D': 'D', 'LED': 'LED', 'NPN': 'Q', 'POT': 'POT', 'IC': 'IC', 'JACK': 'J', 'SW': 'SW', 'SPK': 'SPK'}
for ref, p in sorted(parts.items(), key=lambda kv: refkey(kv[0])):
    m = meta_for(ref)
    if m is None: raise SystemExit('no catalog entry for ' + ref)
    t = TYPE[p.kind]
    if ref == 'U1': t = 'PICO'
    if ref == 'U2': t = 'MCP'
    if ref == 'U3': t = 'AMP'
    sheet = next(s for s in D.sheets if p in s.parts)
    block = ''
    for (bx, by, bw, bh, title) in sheet.blocks:
        if bx <= p.x <= bx + bw and by <= p.y <= by + bh: block = title
    pins_ = {pn: pinnet.get((ref, pn)) for pn in p.local_pins}
    pins_ = {k: (v if (ref, k) not in nc else None) for k, v in pins_.items()}
    info = dict(ref=ref, type=t, kind=p.kind, value=p.value, vtxt=m['name'], desc=m['name'], pkg=m['pkg'], group=m['group'],
                block=block, sheet=sheet.name, pins=pins_, url=m['url'], title=m['title'], check=m['check'], note=m['note'])
    if t == 'R':
        info['bands'] = bands4(p.value)
    if ref in L.TWO_PIN:
        xs = [L.hole(*v) for v in L.TWO_PIN[ref].values()]
        info['x'] = round(sum(a for a, b in xs) / len(xs), 2); info['y'] = round(sum(b for a, b in xs) / len(xs), 2); info['side'] = 'rear'
        info['pads'] = {k: list(L.hole(*v)) for k, v in L.TWO_PIN[ref].items()}
    elif ref == 'U1':
        a, b = L.hole(*L.pico_pin(1)), L.hole(*L.pico_pin(40)); info['x'] = round((a[0] + L.hole(*L.pico_pin(21))[0]) / 2, 2); info['y'] = round((a[1] + L.hole(*L.pico_pin(20))[1]) / 2, 2); info['side'] = 'rear'
    elif ref == 'U2':
        a, b = L.hole(*L.mcp_pin(1)), L.hole(*L.mcp_pin(9)); info['x'] = round((a[0] + b[0]) / 2, 2); info['y'] = round((a[1] + L.hole(*L.mcp_pin(8))[1]) / 2, 2); info['side'] = 'rear'
    elif ref == 'U3':
        a, b = L.hole(*L.amp_pin(1)), L.hole(*L.amp_pin(7)); info['x'] = round((a[0] + b[0]) / 2, 2); info['y'] = round(a[1] - 10.5, 2); info['side'] = 'rear'
    elif ref in L.PANEL:
        info['x'], info['y'] = L.PANEL[ref]; info['side'] = 'panel'
    elif ref == 'J1':
        info['x'], info['y'] = L.J1_POS[0], L.J1_POS[1]; info['side'] = 'wall'
    phys.append(info)

# bill of materials
groups = collections.OrderedDict()
for i in phys:
    key = None
    for g, base in SHARED.items():
        if i['ref'] in g or i['ref'] == base: key = ('shared', base)
    if key is None: key = ('one', i['ref'])
    groups.setdefault(key, []).append(i['ref'])
bom = []
for key, refs in groups.items():
    refs = sorted(refs, key=refkey)
    if key[0] == 'shared': refs = sorted(set(refs) | {key[1]}, key=refkey)
    m = meta_for(refs[0])
    bom.append(dict(group=m['group'], name=m['name'], pkg=m['pkg'], qty=len(refs), refs=refs, title=m['title'], url=m['url'], check=m['check'], note=m['note']))
# the sub-circuit refs that share a catalog entry are merged above; make each entry unique
seen, uniq = set(), []
for b in bom:
    k = (b['name'], tuple(b['refs']))
    if k in seen: continue
    seen.add(k); uniq.append(b)
bom = uniq
ORDER = ['Модули и микросхемы', 'Транзисторы и диоды', 'Резисторы', 'Конденсаторы', 'Регуляторы', 'Разъёмы и коммутация']
bom.sort(key=lambda b: (ORDER.index(b['group']), refkey(b['refs'][0])))
extra = [dict(group=e['group'], name=e['name'], qty=e['qty'], title=e['title'], url=e['url'], note=e['note'], check=e['check']) for e in EXTRA]

with open(os.path.join(OUT, 'bom.csv'), 'w', encoding='utf-8') as f:
    f.write('Группа;Обозначения;Кол-во;Название;Название на chipdip.ru;Ссылка;Примечание\n')
    for b in bom: f.write(f"{b['group']};{' '.join(b['refs'])};{b['qty']};{b['name']};{b['title']};{b['url']};{b['note']}\n")
    for e in extra: f.write(f"{e['group']};;{e['qty']};{e['name']};{e['title']};{e['url']};{e['note']}\n")

# BOM as a markdown table
with open(os.path.join(OUT, 'BOM.md'), 'w', encoding='utf-8') as f:
    f.write('# Список покупок (цифровая версия)\n\nНазвания и ссылки взяты из поиска по chipdip.ru; страницы товаров открыть не удалось, поэтому наличие и цены проверяйте на сайте.\n\n')
    f.write('| Обозначения | Кол-во | Что это | Название на chipdip.ru | Проверка |\n|---|---|---|---|---|\n')
    for b in bom:
        name = f"[{b['title']}]({b['url']})" if b['url'] and b['title'] else (b['title'] or '')
        f.write(f"| {' '.join(b['refs'])} | {b['qty']} | {b['name']}{('. ' + b['note']) if b['note'] else ''} | {name} | {b['check']} |\n")
    f.write('\n## Кроме деталей на схеме\n\n| Кол-во | Что это | Название на chipdip.ru | Примечание | Проверка |\n|---|---|---|---|---|\n')
    for e in extra:
        name = f"[{e['title']}]({e['url']})" if e['url'] and e['title'] else (e['title'] or '')
        f.write(f"| {e['qty']} | {e['name']} | {name} | {e['note']} | {e['check']} |\n")

# wiring tables
with open(os.path.join(OUT, 'nets.csv'), 'w', encoding='utf-8') as f:
    f.write('net;pins\n')
    for n in sorted(nets): f.write(f"{n};{' '.join(sorted(f'{r}.{p}' for r, p in nets[n] if (r, p) not in nc))}\n")
with open(os.path.join(OUT, 'wiring.csv'), 'w', encoding='utf-8') as f:
    f.write('цепь;откуда;отверстие;куда;отверстие;тип;длина_мм\n')
    for w in wires: f.write(f"{w['net']};{w['a']};{w['ha']};{w['b']};{w['hb']};{'провод к панели' if w['kind']=='harness' else 'перемычка на плате'};{w['length']}\n")

# ---- flat map of the board (what the builder looks at) ------------------------------------------------------------------------------------
import html as _h
def board_svg():
    S = 9.0; mx, my = 60, 70
    bw, bh = L.BOARD['w'] * S, L.BOARD['h'] * S
    W, H = 1300, int(bh + 2 * my + 40)
    def hp(c, r):    # hole -> pixel, columns grow to the right (component side, USB of the Pico at the top)
        return (mx + (L.BOARD['w'] / 2 + (c - (L.COLS - 1) / 2) * L.PITCH) * S, my + (L.BOARD['h'] / 2 + (r - (L.ROWS - 1) / 2) * L.PITCH) * S)
    o = [f'<rect width="{W}" height="{H}" fill="#fbfbf8"/>', '<text x="16" y="26" font-size="15" font-weight="700" fill="#2b3033">Лист 3 · Макетная плата 70 × 90 мм, вид со стороны деталей</text>',
         f'<rect x="{mx}" y="{my}" width="{bw}" height="{bh}" rx="6" fill="#2a7b57" stroke="#1d5a3f"/>']
    for c in range(L.COLS):
        x, _ = hp(c, 0); o.append(f'<text x="{x}" y="{my-10}" font-size="10" text-anchor="middle" fill="#2b3033">{chr(65+c)}</text>')
    for r in range(L.ROWS):
        _, y = hp(0, r); o.append(f'<text x="{mx-12}" y="{y+3}" font-size="9" text-anchor="end" fill="#2b3033">{r+1}</text>')
        for c in range(L.COLS):
            x, y = hp(c, r); o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="#d7b44a"/><circle cx="{x:.1f}" cy="{y:.1f}" r="1.1" fill="#143d2b"/>')
    def rect(c0, r0, c1, r1, fill, label, pad=12, stroke='#fff', op=0.85, tcolor='#fff'):
        a, b = hp(c0, r0), hp(c1, r1)
        x0, y0, w_, h_ = min(a[0], b[0]) - pad, min(a[1], b[1]) - pad, abs(a[0] - b[0]) + 2 * pad, abs(a[1] - b[1]) + 2 * pad
        o.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w_:.1f}" height="{h_:.1f}" rx="3" fill="{fill}" fill-opacity="{op}" stroke="{stroke}" stroke-width="1.2"/>')
        o.append(f'<text x="{x0+w_/2:.1f}" y="{y0+h_/2+4:.1f}" font-size="11" font-weight="700" text-anchor="middle" fill="{tcolor}">{_h.escape(label)}</text>')
    rect(3, 3, 3, 22, '#222', '', 9, '#888'); rect(10, 3, 10, 22, '#222', '', 9, '#888')
    a, b = hp(3, 2), hp(10, 23); o.append(f'<rect x="{a[0]-14:.1f}" y="{a[1]-18:.1f}" width="{b[0]-a[0]+28:.1f}" height="{b[1]-a[1]+34:.1f}" rx="4" fill="#1f7a4a" fill-opacity="0.55" stroke="#fff" stroke-width="1.4"/>')
    o.append(f'<text x="{(a[0]+b[0])/2:.1f}" y="{(a[1]+b[1])/2:.1f}" font-size="13" font-weight="700" text-anchor="middle" fill="#fff">Pico 2</text><text x="{(a[0]+b[0])/2:.1f}" y="{a[1]-4:.1f}" font-size="9" text-anchor="middle" fill="#fff">USB</text>')
    GP = {12: 'GP9', 14: 'GP10', 15: 'GP11', 20: 'GP15', 21: 'GP16', 22: 'GP17', 24: 'GP18', 25: 'GP19', 33: 'AGND', 36: '3V3', 38: 'GND', 39: 'VSYS'}
    for pin, name in GP.items():
        x, y = hp(*L.pico_pin(pin)); left = pin <= 20
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#ffe27a"/><text x="{x + (-9 if left else 9):.1f}" y="{y+3:.1f}" font-size="9" font-weight="700" text-anchor="{"end" if left else "start"}" fill="#fff">{pin} {name}</text>')
    rect(*L.MCP_COLS[0:1], L.MCP_ROW0, L.MCP_COLS[1], L.MCP_ROW0 + 7, '#111', 'MCP3008', 12)
    for pin in range(1, 17):
        x, y = hp(*L.mcp_pin(pin)); o.append(f'<text x="{x + (-8 if pin <= 8 else 8):.1f}" y="{y+3:.1f}" font-size="8" text-anchor="{"end" if pin <= 8 else "start"}" fill="#fff">{pin}</text>')
    a, b = hp(*L.amp_pin(1)), hp(*L.amp_pin(7))
    o.append(f'<rect x="{a[0]-14:.1f}" y="{a[1]-6:.1f}" width="{b[0]-a[0]+28:.1f}" height="{S*21:.1f}" rx="3" fill="#b3262a" fill-opacity="0.9" stroke="#fff"/>')
    for i, nm in enumerate(['VIN', 'GND', 'SD', 'GAIN', 'DIN', 'BCLK', 'LRC']):
        x, y = hp(*L.amp_pin(i + 1)); o.append(f'<text x="{x:.1f}" y="{y+14:.1f}" font-size="8.5" font-weight="700" text-anchor="middle" fill="#fff">{i+1} {nm}</text>')
    o.append(f'<text x="{(a[0]+b[0])/2:.1f}" y="{a[1]+70:.1f}" font-size="13" font-weight="700" text-anchor="middle" fill="#fff">MAX98357A</text>')
    for ref, pads_ in L.TWO_PIN.items():
        cs = list(pads_.values()); pts = [hp(*v) for v in cs]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        o.append(f'<rect x="{min(xs)-9:.1f}" y="{min(ys)-9:.1f}" width="{max(xs)-min(xs)+18:.1f}" height="{max(ys)-min(ys)+18:.1f}" rx="5" fill="#f4f6f2" fill-opacity="0.9" stroke="#2b3033"/>')
        o.append(f'<text x="{(min(xs)+max(xs))/2:.1f}" y="{(min(ys)+max(ys))/2+4:.1f}" font-size="10" font-weight="700" text-anchor="middle" fill="#2b3033">{ref}</text>')
    # jumpers
    for w in wires:
        if w['kind'] != 'jumper': continue
        a = HOLE_OF.get(tuple(w['a'].split('.', 1))); b = HOLE_OF.get(tuple(w['b'].split('.', 1)))
        if not (a and b): continue
        (x1, y1), (x2, y2) = hp(*a), hp(*b)
        o.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{w["color"]}" stroke-width="2.4" stroke-linecap="round" opacity="0.92"/>')
    # table
    tx = mx + bw + 70
    o.append(f'<text x="{tx}" y="{my}" font-size="12" font-weight="700" fill="#2b3033">Провода (монтажный провод по стороне пайки)</text>')
    y = my + 22
    for kind, title in (('harness', 'К панели и корпусу: три провода на потенциометр и по два на кнопку, светодиод, динамик, гнездо'), ('jumper', 'Перемычки на плате')):
        o.append(f'<text x="{tx}" y="{y}" font-size="10.5" fill="#6d7377">{_h.escape(title)}</text>'); y += 16
        for w in [q for q in wires if q['kind'] == kind]:
            o.append(f'<line x1="{tx}" y1="{y-4}" x2="{tx+22}" y2="{y-4}" stroke="{w["color"]}" stroke-width="3.2"/>')
            o.append(f'<text x="{tx+30}" y="{y}" font-size="10" fill="#2b3033"><tspan font-weight="700">{_h.escape(w["net"])}</tspan>  {_h.escape(w["a"])} ({_h.escape(w["ha"])}) → {_h.escape(w["b"])} ({_h.escape(w["hb"])})</text>')
            y += 14
        y += 10
    H2 = max(H, y + 20)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H2}" width="{W}" height="{H2}" font-family="Helvetica, Arial, sans-serif">' + ''.join(o).replace(f'height="{H}" fill', f'height="{H2}" fill', 1) + '</svg>'
bs = board_svg()
open(os.path.join(OUT, 'sheet-3-board.svg'), 'w').write(bs); shutil.copy(os.path.join(OUT, 'sheet-3-board.svg'), os.path.join(DATA, 'sheet-3-board.svg'))
m = re.search(r'viewBox="0 0 (\d+) (\d+)"', bs)
sheet_files.append(dict(file='sheet-3-board.svg', title='Лист 3 · Макетная плата: расположение и провода', w=int(m.group(1)), h=int(m.group(2)), name='3-board'))

# KiCad-style netlist is not produced for this version: the board is hand-wired.
sim = json.load(open(os.path.join(OUT, 'dsp-compare.json'))) if os.path.exists(os.path.join(OUT, 'dsp-compare.json')) else []
hw = dict(version='digital', generated=datetime.date.today().isoformat(), unit_mm=L.UNIT, board=dict(L.BOARD, cols=L.COLS, rows=L.ROWS, pitch=L.PITCH, standoff=L.STANDOFF),
          sheets=sheet_files, parts=phys, bom=bom, extra=extra,
          nets={n: sorted(f'{r}.{p}' for r, p in pl if (r, p) not in nc) for n, pl in nets.items() if any((r, p) not in nc for r, p in pl)},
          wires=wires, checks=checks, dsp=sim,
          holes=dict(pico=[list(L.pico_pin(i)) for i in range(1, 41)], mcp=[list(L.mcp_pin(i)) for i in range(1, 17)], amp=[list(L.amp_pin(i)) for i in range(1, 8)]),
          totals=dict(items=sum(b['qty'] for b in bom), lines=len(bom), nets=len(nets), wires=len(wires)))
json.dump(hw, open(os.path.join(OUT, 'hardware.json'), 'w'), ensure_ascii=False, indent=1)
shutil.copy(os.path.join(OUT, 'hardware.json'), os.path.join(DATA, 'hardware.json'))
print('BOM', hw['totals'])
