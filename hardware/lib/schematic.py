"""Tiny schematic-capture DSL.

The drawing is the single source of truth: parts, wires and net labels placed
here give the connectivity, from which the SPICE netlist, the BOM and an ERC
report are derived. If a wire is missing in the drawing it is missing in the
netlist and the simulation shows it.
"""
import math, re, collections, html

INK = '#2b3033'
SOFT = '#6d7377'
ACCENT = '#00a79b'   # darker teal so lines read on white
BG = '#fbfbf8'

def rot(p, deg):
    c, s = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}[deg % 360]
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c)


class Part:
    def __init__(self, ref, kind, value, x, y, rot_, pins, meta):
        self.ref, self.kind, self.value = ref, kind, value
        self.x, self.y, self.rot = x, y, rot_
        self.local_pins = pins            # pin name -> local (x, y)
        self.meta = meta
        self.pin_xy = {n: self._abs(p) for n, p in pins.items()}

    def _abs(self, p):
        r = rot(p, self.rot)
        return (int(round(self.x + r[0])), int(round(self.y + r[1])))


class Sheet:
    def __init__(self, name, title, w, h):
        self.name, self.title, self.w, self.h = name, title, w, h
        self.parts = []
        self.wires = []     # list of point lists
        self.dots = []
        self.labels = []    # (net, x, y, kind)
        self.svg_items = [] # drawing fragments (strings)
        self.notes = []
        self.blocks = []

    # --- primitive helpers ------------------------------------------------
    def wire(self, *pts):
        pts = [(int(round(x)), int(round(y))) for x, y in pts]
        self.wires.append(pts)
        self.svg_items.append(
            f'<polyline points="{" ".join(f"{x},{y}" for x, y in pts)}" fill="none" stroke="{INK}" stroke-width="1.4" stroke-linejoin="round"/>')

    def dot(self, x, y):
        self.dots.append((int(round(x)), int(round(y))))
        self.svg_items.append(f'<circle cx="{x}" cy="{y}" r="3" fill="{INK}"/>')

    def label(self, net, x, y, side='r', kind='flag'):
        """Named net flag. Everything sharing a name is one net."""
        x, y = int(round(x)), int(round(y))
        self.labels.append((net, x, y))
        if kind == 'gnd':
            self.svg_items.append(
                f'<g stroke="{INK}" stroke-width="1.4" fill="none"><line x1="{x}" y1="{y}" x2="{x}" y2="{y+6}"/><line x1="{x-9}" y1="{y+6}" x2="{x+9}" y2="{y+6}"/><line x1="{x-5.5}" y1="{y+10}" x2="{x+5.5}" y2="{y+10}"/><line x1="{x-2}" y1="{y+14}" x2="{x+2}" y2="{y+14}"/></g>')
        elif kind == 'rail':
            self.svg_items.append(
                f'<g stroke="{ACCENT}" stroke-width="1.6" fill="none"><line x1="{x}" y1="{y}" x2="{x}" y2="{y-8}"/><line x1="{x-8}" y1="{y-8}" x2="{x+8}" y2="{y-8}"/></g>'
                f'<text x="{x}" y="{y-13}" text-anchor="middle" font-size="9" font-weight="600" fill="{ACCENT}">{html.escape(net)}</text>')
        else:
            anchor = {'r': 'start', 'l': 'end'}[side]
            dx = 8 if side == 'r' else -8
            tip = 6 if side == 'r' else -6
            self.svg_items.append(
                f'<g><polyline points="{x},{y} {x+tip},{y-4} {x+tip*2.2},{y-4} {x+tip*2.2},{y+4} {x+tip},{y+4} {x},{y}" fill="none" stroke="{SOFT}" stroke-width="1"/></g>'
                f'<text x="{x+ (tip*2.2+4 if side=="r" else tip*2.2-4)}" y="{y+3}" text-anchor="{anchor}" font-size="9" fill="{INK}">{html.escape(net)}</text>')

    def gnd(self, x, y):
        self.label('GND', x, y, kind='gnd')

    def rail(self, net, x, y):
        self.label(net, x, y, kind='rail')

    def text(self, x, y, s, size=10, weight=400, anchor='start', fill=None):
        self.svg_items.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{fill or INK}">{html.escape(s)}</text>')

    def block(self, x, y, w, h, title):
        self.blocks.append((x, y, w, h, title))
        self.svg_items.insert(0,
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="none" stroke="{SOFT}" stroke-width="0.8" stroke-dasharray="4 3"/>'
            f'<text x="{x+10}" y="{y+16}" font-size="11" font-weight="700" letter-spacing="1" fill="{SOFT}">{html.escape(title.upper())}</text>')

    def note(self, x, y, s):
        self.text(x, y, s, size=9, fill=SOFT)

    # --- parts ------------------------------------------------------------
    def add(self, ref, kind, value, x, y, r, pins, svg, meta, label_off=None):
        p = Part(ref, kind, value, x, y, r, pins, meta)
        self.parts.append(p)
        self.svg_items.append(f'<g transform="translate({x},{y}) rotate({r})" stroke="{INK}" stroke-width="1.4" fill="none" stroke-linecap="round" stroke-linejoin="round">{svg}</g>')
        if label_off is not None and ref:
            lx, ly, anchor = label_off[:3]
            vy = label_off[3] if len(label_off) > 3 else 11
            self.text(x + lx, y + ly, ref, size=10, weight=700, anchor=anchor)
            if value:
                self.text(x + lx, y + ly + vy, disp(value), size=9, anchor=anchor, fill=SOFT)
        return p

    def R(self, ref, value, x, y, r=0, **meta):
        svg = '<line x1="-20" y1="0" x2="-11" y2="0"/><rect x="-11" y="-4.5" width="22" height="9"/><line x1="11" y1="0" x2="20" y2="0"/>'
        off = (0, -9, 'middle', 29) if r % 180 == 0 else (10, -2, 'start', 11)
        return self.add(ref, 'R', value, x, y, r, {'1': (-20, 0), '2': (20, 0)}, svg, meta, off)

    def C(self, ref, value, x, y, r=0, polar=False, **meta):
        svg = ('<line x1="-20" y1="0" x2="-3" y2="0"/><line x1="-3" y1="-8" x2="-3" y2="8"/>'
               + ('<path d="M 4,-8 Q 1,0 4,8"/>' if polar else '<line x1="3" y1="-8" x2="3" y2="8"/>')
               + '<line x1="3" y1="0" x2="20" y2="0"/>')
        if polar:
            svg += '<text x="-13" y="-6" font-size="9" stroke="none" fill="#2b3033">+</text>'
        off = (0, -14, 'middle', 33) if r % 180 == 0 else (13, -2, 'start', 11)
        return self.add(ref, 'CP' if polar else 'C', value, x, y, r, {'1': (-20, 0), '2': (20, 0)}, svg, meta, off)

    def POT(self, ref, value, x, y, r=0, trim=False, **meta):
        svg = ('<line x1="-20" y1="0" x2="-11" y2="0"/><rect x="-11" y="-4.5" width="22" height="9"/><line x1="11" y1="0" x2="20" y2="0"/>'
               '<line x1="0" y1="-20" x2="0" y2="-12"/><polyline points="-3.5,-6 0,-12 3.5,-6" fill="none"/>'
               + ('<line x1="-9" y1="-13" x2="9" y2="-5"/>' if trim else ''))
        off = (0, 22, 'middle', 11) if r % 180 == 0 else (14, 4, 'start')
        return self.add(ref, 'POT', value, x, y, r, {'1': (-20, 0), 'W': (0, -20), '3': (20, 0)}, svg, meta, off)

    def D(self, ref, value, x, y, r=0, led=False, **meta):
        svg = ('<line x1="-20" y1="0" x2="-6" y2="0"/><polygon points="-6,-7 -6,7 6,0" fill="none"/><line x1="6" y1="-7" x2="6" y2="7"/><line x1="6" y1="0" x2="20" y2="0"/>')
        if led:
            svg += '<line x1="-2" y1="-9" x2="4" y2="-15"/><polyline points="1.5,-15 4,-15 4,-12.5"/><line x1="3" y1="-6" x2="9" y2="-12"/><polyline points="6.5,-12 9,-12 9,-9.5"/>'
        off = (0, -12 if not led else -22, 'middle', 31 if not led else 40) if r % 180 == 0 else (13, -2, 'start', 11)
        return self.add(ref, 'LED' if led else 'D', value, x, y, r, {'A': (-20, 0), 'K': (20, 0)}, svg, meta, off)

    def NPN(self, ref, value, x, y, r=0, **meta):
        svg = ('<line x1="-20" y1="0" x2="-4" y2="0"/><line x1="-4" y1="-9" x2="-4" y2="9"/><line x1="-4" y1="-4" x2="10" y2="-12"/><line x1="10" y1="-12" x2="10" y2="-20"/>'
               '<line x1="-4" y1="4" x2="10" y2="12"/><line x1="10" y1="12" x2="10" y2="20"/><polygon points="10,12 4,11.5 7,6.5" fill="#2b3033"/>')
        return self.add(ref, 'NPN', value, x, y, r, {'B': (-20, 0), 'C': (10, -20), 'E': (10, 20)}, svg, meta, (24, 0, 'start', 11))

    def OP(self, ref, unit, ic_ref, value, x, y, pins, r=0, **meta):
        """Op-amp unit. pins: {'+': pin#, '-': pin#, 'O': pin#}."""
        svg = ('<polygon points="-18,-22 -18,22 26,0" fill="none"/>'
               '<line x1="-30" y1="-10" x2="-18" y2="-10"/><line x1="-30" y1="10" x2="-18" y2="10"/><line x1="26" y1="0" x2="30" y2="0"/>'
               '<text x="-15" y="-6.5" font-size="11" stroke="none" fill="#2b3033">+</text><text x="-15" y="14" font-size="11" stroke="none" fill="#2b3033">&#8722;</text>')
        meta = dict(meta, unit=unit, ic=ic_ref, pinmap=pins)
        p = self.add(f'{ic_ref}{unit}', 'OP', value, x, y, r, {'+': (-30, -10), '-': (-30, 10), 'O': (30, 0)}, svg, meta, None)
        self.text(x - 2, y - 28, f'{ic_ref}{unit}', size=10, weight=700, anchor='middle')
        self.text(x - 2, y + 38, disp(value), size=9, anchor='middle', fill=SOFT)
        # pin numbers
        for name, (lx, ly) in {'+': (-30, -10), '-': (-30, 10), 'O': (30, 0)}.items():
            ax, ay = rot((lx, ly), r)
            off = {'+': (-3, -4), '-': (-3, 12), 'O': (3, -4)}[name]
            ox, oy = rot(off, r) if r else off
            self.text(x + ax + ox + (0 if name == 'O' else 0), y + ay + oy, str(pins[name]), size=8, fill=SOFT, anchor='end' if name != 'O' else 'start')
        return p

    def PWR(self, ref, value, x, y, vp, vm, vp_name='V+', vm_name='V-', r=0, **meta):
        """Supply pins of a multi-unit IC (drawn as a small box)."""
        svg = f'<rect x="-14" y="-10" width="28" height="20" fill="none"/><text x="0" y="3" font-size="8" text-anchor="middle" stroke="none" fill="#2b3033">PWR</text><line x1="0" y1="-20" x2="0" y2="-10"/><line x1="0" y1="10" x2="0" y2="20"/>'
        meta = dict(meta, ic=ref, pinmap={'VP': vp, 'VM': vm})
        p = self.add(f'{ref}P', 'PWR', value, x, y, r, {'VP': (0, -20), 'VM': (0, 20)}, svg, meta, None)
        self.text(x + 18, y - 2, f'{ref} power', size=9, weight=700)
        self.text(x + 18, y + 9, f'pins {vp} / {vm}', size=8, fill=SOFT)
        return p

    def BOX(self, ref, value, x, y, left, right, w=120, r=0, top=None, bottom=None, spacing=20, **meta):
        """Generic IC box. left/right: list of (pin#, label). Pin names are the pin numbers."""
        n = max(len(left), len(right))
        h = (n + 1) * spacing
        pins, svg = {}, [f'<rect x="{-w/2}" y="{-h/2}" width="{w}" height="{h}" fill="#fff"/>']
        texts = []
        for i, (pn, lab) in enumerate(left):
            yy = -h / 2 + spacing * (i + 1)
            if pn is not None:
                pins[str(pn)] = (-w / 2 - 20, yy)
                svg.append(f'<line x1="{-w/2-20}" y1="{yy}" x2="{-w/2}" y2="{yy}"/>')
                texts.append((-w / 2 + 5, yy + 3, lab, 'start'))
                texts.append((-w / 2 - 17, yy - 3, str(pn), 'start'))
        for i, (pn, lab) in enumerate(right):
            yy = -h / 2 + spacing * (i + 1)
            if pn is not None:
                pins[str(pn)] = (w / 2 + 20, yy)
                svg.append(f'<line x1="{w/2}" y1="{yy}" x2="{w/2+20}" y2="{yy}"/>')
                texts.append((w / 2 - 5, yy + 3, lab, 'end'))
                texts.append((w / 2 + 17, yy - 3, str(pn), 'end'))
        meta = dict(meta, pinmap={k: k for k in pins})
        p = self.add(ref, 'IC', value, x, y, r, pins, ''.join(svg), meta, None)
        for tx, ty, lab, anc in texts:
            gx, gy = rot((tx, ty), r)
            self.text(x + gx, y + gy, lab, size=8.5 if lab.isdigit() is False and len(lab) > 0 and not lab.isdigit() else 8, anchor=anc, fill=SOFT if lab.isdigit() else INK)
        self.text(x, y - h / 2 - 6, f'{ref}  {value}', size=10, weight=700, anchor='middle')
        return p

    def custom(self, ref, kind, value, x, y, pins, svg, meta, label=None, r=0):
        p = self.add(ref, kind, value, x, y, r, pins, svg, meta, label)
        return p

    # --- output -----------------------------------------------------------
    def svg(self):
        body = '\n'.join(self.svg_items)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" font-family="Helvetica, Arial, sans-serif">'
                f'<rect width="{self.w}" height="{self.h}" fill="{BG}"/>'
                f'<text x="16" y="24" font-size="15" font-weight="700" fill="{INK}">{html.escape(self.title)}</text>'
                f'{body}</svg>')


def disp(v):
    return str(v).replace('u', 'µ') if re.match(r'^[0-9.]+u$', str(v)) else str(v)


class Design:
    def __init__(self):
        self.sheets = []

    def sheet(self, *a, **k):
        s = Sheet(*a, **k); self.sheets.append(s); return s

    # connectivity ---------------------------------------------------------
    def nets(self):
        parent = {}
        def find(a):
            parent.setdefault(a, a)
            while parent[a] != a:
                parent[a] = parent[parent[a]]; a = parent[a]
            return a
        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb: parent[ra] = rb
        pin_at = collections.defaultdict(list)
        names = collections.defaultdict(set)
        for si, sh in enumerate(self.sheets):
            def key(pt): return (si, pt[0], pt[1])
            for w in sh.wires:
                for a, b in zip(w, w[1:]):
                    union(key(a), key(b))
                    find(key(a))
            for dx, dy in sh.dots:
                for w in sh.wires:
                    for a, b in zip(w, w[1:]):
                        if on_segment((dx, dy), a, b):
                            union(key((dx, dy)), key(a))
            for p in sh.parts:
                for pn, xy in p.pin_xy.items():
                    find(key(xy)); pin_at[key(xy)].append((p.ref, pn))
            for net, x, y in sh.labels:
                find(key((x, y))); names[net].add(key((x, y)))
        # global net names
        for net, ks in names.items():
            ks = list(ks)
            for k in ks[1:]:
                union(ks[0], k)
        groups = collections.defaultdict(list)
        for k, items in pin_at.items():
            groups[find(k)].extend(items)
        net_name = {}
        for net, ks in names.items():
            net_name[find(list(ks)[0])] = net
        out, n = {}, 0
        for root, pins in groups.items():
            nm = net_name.get(root)
            if nm is None:
                n += 1; nm = f'N{n:03d}'
            out.setdefault(nm, []).extend(pins)
        return out

    def parts(self):
        d = {}
        for sh in self.sheets:
            for p in sh.parts:
                if p.ref in d: raise ValueError('duplicate ref ' + p.ref)
                d[p.ref] = p
        return d


def on_segment(pt, a, b):
    (x, y), (x1, y1), (x2, y2) = pt, a, b
    if (x2 - x1) * (y - y1) != (y2 - y1) * (x - x1): return False
    return min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2)
