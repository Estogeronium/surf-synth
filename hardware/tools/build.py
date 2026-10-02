"""Render the schematic sheets and derive every other deliverable from them."""
import sys, os, json, shutil, collections, re, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import circuit, spice, parts_meta as pm, layout
D = circuit.D
OUT = os.path.join(HERE, '..', 'out')
DATA = os.path.join(HERE, '..', '..', 'src', 'hardware-data')
os.makedirs(OUT, exist_ok=True); os.makedirs(DATA, exist_ok=True)

nets = D.nets()
parts = D.parts()

# ---- sheets -----------------------------------------------------------------
sheet_files = []
for sh in D.sheets:
    fn = f'sheet-{sh.name}.svg'
    open(os.path.join(OUT, fn), 'w').write(sh.svg())
    shutil.copy(os.path.join(OUT, fn), os.path.join(DATA, fn))
    sheet_files.append(dict(file=fn, title=sh.title, w=sh.w, h=sh.h, name=sh.name))

# ---- ERC --------------------------------------------------------------------
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
print(len(parts), 'drawn symbols,', len(nets), 'nets, ERC problems:', bad)
if bad: sys.exit(1)

# ---- block of every part ----------------------------------------------------
part_sheet = {}
part_block = {}
for sh in D.sheets:
    for p in sh.parts:
        part_sheet[p.ref] = sh
        for (bx, by, bw, bh, title) in sh.blocks:
            if bx <= p.x <= bx + bw and by <= p.y <= by + bh:
                part_block[p.ref] = title

# ---- physical parts (ICs merge their op-amp / power units) -----------------------
def ic_pin_nets(icref):
    out = {}
    for ref, p in parts.items():
        if p.kind in ('OP', 'PWR') and p.meta['ic'] == icref:
            for name, num in p.meta['pinmap'].items():
                out[str(num)] = pinnet.get((ref, name))
        elif ref == icref and p.kind == 'IC':
            for pn in p.local_pins: out[str(pn)] = pinnet.get((ref, pn))
    return out

phys = []
for ref, p in parts.items():
    if p.kind in ('OP', 'PWR'):
        continue
    pin_nets = {pn: pinnet.get((ref, pn)) for pn in p.local_pins}
    if p.kind == 'IC': pin_nets = ic_pin_nets(ref)
    info = pm.describe(p, [n for n in pin_nets.values() if n])
    if info is None: continue
    info.update(ref=ref, value=p.value, kind=p.kind, block=part_block.get(ref, ''), sheet=part_sheet[ref].name,
                pins={k: v for k, v in pin_nets.items()})
    phys.append(info)
# ICs that only exist as op-amp units
for icref in sorted({p.meta['ic'] for p in parts.values() if p.kind in ('OP', 'PWR')} - {r for r, p in parts.items() if p.kind == 'IC'}):
    val = next(p.value for p in parts.values() if p.kind == 'OP' and p.meta['ic'] == icref)
    class _P: pass
    fake = _P(); fake.kind = 'IC'; fake.value = val; fake.ref = icref
    info = pm.describe(fake, [])
    pn = ic_pin_nets(icref)
    blk = part_block.get(icref + 'A') or part_block.get(icref + 'P') or ''
    info.update(ref=icref, value=val, kind='IC', block=blk, sheet=(part_sheet.get(icref + 'A') or part_sheet[icref + 'P']).name, pins=pn)
    phys.append(info)

def refkey(r): return (re.match(r'[A-Z]+', r).group(), int(re.search(r'\d+', r).group()), r)
phys.sort(key=lambda i: refkey(i['ref']))
print(len(phys), 'physical parts')

# ---- placement ------------------------------------------------------------------
items = []
for i in phys:
    ref = i['ref']
    if ref in ('SW1', 'D10', 'RV3', 'RV4', 'RV5', 'RV6A', 'RV6B', 'J1', 'SPK1'): continue
    fp = pm.FP[i['fp']]
    t = layout.TARGETS.get(i['block'], (40, 0))
    area = fp['w'] * fp['d']
    items.append(dict(ref=ref, w=fp['w'], d=fp['d'], target=t, near=layout.NEAR.get(ref), area=area, block=i['block'], rotate=i['type'] in ('IC',) and False))
# big parts first, then those that want to be near another part
order = sorted(items, key=lambda it: (it['near'] is not None, -it['area']))
placed = layout.place(order)
for i in phys:
    ref = i['ref']; fp = pm.FP[i['fp']]
    i['fp_dim'] = dict(w=fp['w'], d=fp['d'], h=fp['h'])
    i['kicad'] = fp['kicad']
    if ref in placed:
        x, y, rot = placed[ref]; i['x'], i['y'], i['rot'] = round(x, 2), round(y, 2), rot; i['side'] = 'rear'
    elif ref in ('RV5',): i['x'], i['y'] = layout.PANEL['RV5']; i['rot'] = 0; i['side'] = 'front'
    elif ref in ('RV3', 'RV4'): i['x'], i['y'] = layout.PANEL[ref]; i['rot'] = 0; i['side'] = 'front'
    elif ref in ('RV6A', 'RV6B'): i['x'], i['y'] = layout.PANEL['RV6']; i['rot'] = 0; i['side'] = 'front'
    elif ref == 'SW1': i['x'], i['y'] = layout.PANEL['SW1']; i['rot'] = 0; i['side'] = 'front'
    elif ref == 'D10': i['x'], i['y'] = layout.PANEL['D10']; i['rot'] = 0; i['side'] = 'front'
    elif ref == 'J1': i['x'], i['y'] = layout.J1_POS; i['rot'] = 0; i['side'] = 'rear'
    elif ref == 'SPK1': i['x'], i['y'] = -2.15 * layout.UNIT, -0.05 * layout.UNIT; i['rot'] = 0; i['side'] = 'front'
    for k in ('x', 'y'): i[k] = round(float(i[k]), 2)

# ---- BOM ------------------------------------------------------------------------
groups = collections.OrderedDict()
for i in phys:
    if i['ref'] == 'RV6B': continue
    key = (i['group'], i['desc'], i['pkg'], i['value'] if i['type'] in ('R', 'C') else '')
    if i['type'] in ('IC', 'D', 'Q', 'POT', 'J', 'SW', 'SPK', 'LED'): key = (i['group'], i['desc'], i['pkg'], i['value'])
    groups.setdefault(key, []).append(i['ref'])
GROUP_ORDER = ['Микросхемы', 'Транзисторы', 'Диоды', 'Регуляторы', 'Резисторы', 'Конденсаторы', 'Разъёмы и коммутация']
bom = []
for (group, desc, pkg, val), refs in groups.items():
    refs = sorted(refs, key=refkey)
    if refs == ['RV6A']: refs = ['RV6']; desc = 'Сдвоенный потенциометр 1 МОм линейный (B1M), две секции'
    bom.append(dict(group=group, desc=desc, pkg=pkg, qty=len(refs), refs=refs))
bom.sort(key=lambda b: (GROUP_ORDER.index(b['group']), refkey(b['refs'][0])))
total = sum(b['qty'] for b in bom)
print('BOM lines', len(bom), 'items', total)

with open(os.path.join(OUT, 'bom.csv'), 'w', encoding='utf-8') as f:
    f.write('Группа;Обозначения;Кол-во;Описание;Корпус / примечание\n')
    for b in bom:
        f.write(f"{b['group']};{' '.join(b['refs'])};{b['qty']};{b['desc']};{b['pkg']}\n")
    for name, d, q in pm.EXTRA_BOM:
        f.write(f"Прочее;;{q};{name};{d}\n")

# ---- nets, SPICE, KiCad ----------------------------------------------------------
with open(os.path.join(OUT, 'nets.csv'), 'w', encoding='utf-8') as f:
    f.write('net;pins\n')
    for n in sorted(nets):
        pins = []
        for r, p in nets[n]:
            if parts[r].kind in ('OP', 'PWR'):
                pins.append(f"{parts[r].meta['ic']}.{parts[r].meta['pinmap'][p]}")
            else: pins.append(f'{r}.{p}')
        f.write(f"{n};{' '.join(sorted(pins))}\n")

nl = spice.export(D, extra='* Add your own analysis, e.g.:\n* .tran 20u 2\n* Noise: replace "DC 0" in Vnoise with a PWL/trnoise source (see tools/simrun.py).\n.end')
open(os.path.join(OUT, 'surf-synth.cir'), 'w').write(nl)

kic = ['(export (version D)', ' (design (source "surf-synth") (tool "surf-synth tools"))', ' (components']
phys_by_ref = {i['ref']: i for i in phys}
for i in phys:
    if i['ref'] == 'RV6B': continue
    val = i['value'] if i['ref'] != 'RV6A' else '1M dual'
    ref = 'RV6' if i['ref'] == 'RV6A' else i['ref']
    kic.append(f'  (comp (ref {ref}) (value "{val}") (footprint "{i["kicad"]}"))')
kic.append(' )')
kic.append(' (nets')
code = 0
def kpin(ref, pin):
    p = parts[ref]
    if p.kind in ('OP', 'PWR'): return p.meta['ic'], str(p.meta['pinmap'][pin])
    if p.kind == 'D' or p.kind == 'LED': return ref, {'K': '1', 'A': '2'}[pin]
    if p.kind == 'NPN': return ref, {'E': '1', 'B': '2', 'C': '3'}[pin]
    if p.kind == 'POT': return ('RV6' if ref.startswith('RV6') else ref), {'1': '1', 'W': '2', '3': '3'}[pin] if not ref.startswith('RV6') else {'1': '1', 'W': '2', '3': '3'}[pin] if ref == 'RV6A' else {'1': '4', 'W': '5', '3': '6'}[pin]
    if p.kind == 'JACK': return ref, {'TIP': '1', 'SLV': '2'}[pin]
    return ref, pin
for n in sorted(nets):
    code += 1
    nodes = sorted({kpin(r, p) for r, p in nets[n] if (r, p) not in nc})
    if not nodes: continue
    kic.append(f'  (net (code {code}) (name "{n}")')
    for r, p in nodes: kic.append(f'   (node (ref {r}) (pin {p}))')
    kic.append('  )')
kic.append(' )')
kic.append(')')
open(os.path.join(OUT, 'surf-synth.net'), 'w').write('\n'.join(kic))

# ---- hardware.json for the web app -----------------------------------------------------
def netlist_for_json():
    d = {}
    for n, pins in nets.items():
        arr = []
        for r, p in pins:
            if (r, p) in nc: continue
            if parts[r].kind in ('OP', 'PWR'): arr.append(f"{parts[r].meta['ic']}.{parts[r].meta['pinmap'][p]}")
            else: arr.append(f'{r}.{p}')
        if arr: d[n] = sorted(set(arr))
    return d

sim = {}
simp = os.path.join(OUT, 'sim-summary.json')
if os.path.exists(simp): sim = json.load(open(simp))

hw = dict(
    generated=datetime.date.today().isoformat(),
    unit_mm=layout.UNIT, board=layout.BOARD,
    sheets=sheet_files,
    parts=[{k: v for k, v in i.items() if k not in ('kicad',)} for i in phys],
    bom=bom, extra=[dict(name=a, desc=b, qty=c) for a, b, c in pm.EXTRA_BOM],
    nets=netlist_for_json(), sim=sim, totals=dict(items=total, lines=len(bom), parts=len(phys), nets=len(nets)),
)
json.dump(hw, open(os.path.join(OUT, 'hardware.json'), 'w'), ensure_ascii=False, indent=1)
shutil.copy(os.path.join(OUT, 'hardware.json'), os.path.join(DATA, 'hardware.json'))
print('wrote outputs to', os.path.normpath(OUT))
