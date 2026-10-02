"""Surf Synth analog surf generator: the schematic is the source of truth.

Parts are placed on sheets; connections are drawn as wires or as net flags
(every flag with the same name is the same net). `build.py` renders SVG,
exports a SPICE netlist and the BOM, and runs an electrical rule check.
"""
from schematic import Design, rot, INK, SOFT, ACCENT

RAILS = {'V12', 'A12', 'VB'}
D = Design()


def outward(part, pin):
    lx, ly = part.local_pins[pin]
    d = (1 if lx > 0 else -1, 0) if abs(lx) >= abs(ly) else (0, 1 if ly > 0 else -1)
    return rot(d, part.rot)


def at(sh, part, pin, net):
    """Attach a net name to a pin: ground symbol, supply symbol or a flag."""
    x, y = part.pin_xy[pin]
    ox, oy = outward(part, pin)
    if net == 'GND':
        sh.label('GND', x, y, kind='gnd')
    elif net in RAILS and (ox, oy) == (0, -1):
        sh.rail(net, x, y)
    elif net in RAILS and ox != 0:
        sx = x + ox * 14
        sh.wire((x, y), (sx, y))
        sh.rail(net, sx, y)
    elif net in RAILS:
        sh.label(net, x, y, side='r')
    else:
        sh.label(net, x, y, side='r' if ox >= 0 else 'l')


def nc(sh, part, pin):
    x, y = part.pin_xy[pin]
    sh.svg_items.append(f'<g stroke="{SOFT}" stroke-width="1.2"><line x1="{x-4}" y1="{y-4}" x2="{x+4}" y2="{y+4}"/><line x1="{x-4}" y1="{y+4}" x2="{x+4}" y2="{y-4}"/></g>')
    sh.nc_pins = getattr(sh, 'nc_pins', []) + [(part.ref, pin)]


def conn(sh, part, **nets):
    for pin, net in nets.items():
        if pin == 'p': pin = '+'
        if pin == 'm': pin = '-'
        if pin == 'o': pin = 'O'
        if net == 'NC': nc(sh, part, pin)
        else: at(sh, part, pin, net)
    return part


def R(sh, ref, val, x, y, a, b, v=False, **kw):
    p = sh.R(ref, val, x, y, 90 if v else 0, **kw)
    return conn(sh, p, **{'1': a, '2': b})


def C(sh, ref, val, x, y, a, b, v=True, polar=False, **kw):
    p = sh.C(ref, val, x, y, 90 if v else 0, polar=polar, **kw)
    return conn(sh, p, **{'1': a, '2': b})


def Dio(sh, ref, val, x, y, a, k, v=False, led=False):
    p = sh.D(ref, val, x, y, 90 if v else 0, led=led)
    return conn(sh, p, **{'A': a, 'K': k})


# ---- custom symbols --------------------------------------------------------
def jack(sh, ref, x, y):
    svg = ('<rect x="-34" y="-18" width="26" height="36" rx="3" fill="none"/>'
           '<line x1="-8" y1="-10" x2="20" y2="-10"/><line x1="-8" y1="10" x2="20" y2="10"/>'
           '<circle cx="-21" cy="0" r="7"/><circle cx="-21" cy="0" r="2" fill="#2b3033"/>')
    p = sh.custom(ref, 'JACK', 'DC 5.5/2.1', x, y, {'TIP': (20, -10), 'SLV': (20, 10)}, svg, {}, None)
    sh.text(x - 21, y - 24, ref, size=10, weight=700, anchor='middle')
    sh.text(x - 21, y + 34, 'гнездо DC 5,5/2,1', size=8.5, anchor='middle', fill=SOFT)
    sh.text(x - 21, y + 45, 'центр «+», 12 В', size=8.5, anchor='middle', fill=SOFT)
    return p


def switch(sh, ref, val, x, y):
    svg = ('<line x1="-20" y1="0" x2="-8" y2="0"/><circle cx="-8" cy="0" r="2.2"/><line x1="-8" y1="0" x2="9" y2="-10"/>'
           '<circle cx="10" cy="0" r="2.2"/><line x1="12" y1="0" x2="20" y2="0"/>'
           '<line x1="0" y1="-14" x2="0" y2="-7" stroke-dasharray="2 2"/><rect x="-7" y="-20" width="14" height="6"/>')
    return sh.custom(ref, 'SW', val, x, y, {'1': (-20, 0), '2': (20, 0)}, svg, {}, (0, 24, 'middle'))


def speaker(sh, ref, x, y):
    svg = ('<rect x="-4" y="-8" width="12" height="16"/><polygon points="8,-8 20,-16 20,16 8,8"/>'
           '<line x1="-20" y1="-4" x2="-4" y2="-4"/><line x1="-20" y1="4" x2="-4" y2="4"/>')
    p = sh.custom(ref, 'SPK', '8R', x, y, {'1': (-20, -4), '2': (-20, 4)}, svg, {}, None)
    sh.text(x + 4, y - 24, ref, size=10, weight=700, anchor='middle')
    sh.text(x + 4, y + 32, 'динамик 8 Ω', size=8.5, anchor='middle', fill=SOFT)
    return p


def opamp(sh, ic, unit, val, x, y, pins, **nets):
    p = sh.OP(unit, unit, ic, val, x, y, pins)  # ref becomes ic+unit
    return conn(sh, p, **nets)


def power_unit(sh, ic, val, x, y, vp, vm, vp_net, vm_net):
    p = sh.PWR(ic, val, x, y, vp, vm)
    at(sh, p, 'VP', vp_net)
    at(sh, p, 'VM', vm_net)
    return p


def pot(sh, ref, val, x, y, p1, w, p3, trim=False, label=None):
    p = sh.POT(ref, val, x, y, 0, trim=trim)
    conn(sh, p, **{'1': p1, 'W': w, '3': p3})
    return p


# ===========================================================================
# SHEET 1 — power, noise source, pink filter
# ===========================================================================
s1 = D.sheet('1-power-noise', 'Лист 1 · Питание, источник шума, розовый фильтр', 1560, 820)

s1.block(20, 40, 760, 200, 'Питание 12 В')
j1 = jack(s1, 'J1', 80, 120)
d1 = s1.D('D1', '1N5819', 190, 110)
sw1 = switch(s1, 'SW1', 'кнопка с фикс.', 290, 110)
s1.wire(j1.pin_xy['TIP'], d1.pin_xy['A'])
s1.wire(d1.pin_xy['K'], sw1.pin_xy['1'])
at(s1, j1, 'SLV', 'GND')
s1.wire(sw1.pin_xy['2'], (360, 110))
s1.rail('V12', 360, 110)
s1.wire((360, 110), (640, 110)); s1.dot(360, 110)
c1 = C(s1, 'C1', '220u', 360, 160, 'V12', 'GND', polar=True)
c2 = C(s1, 'C2', '100n', 430, 160, 'V12', 'GND')
r1 = R(s1, 'R1', '22', 510, 110, 'V12', 'A12')
c3 = C(s1, 'C3', '100u', 620, 160, 'A12', 'GND', polar=True)
c4 = C(s1, 'C4', '100n', 700, 160, 'A12', 'GND')
s1.note(36, 228, 'D1 защищает от неверной полярности блока питания. R1+C3 отделяют малошумящую шину A12 от шины V12.')

s1.block(800, 40, 740, 200, 'Средняя точка VB ≈ 6 В (искусственная «земля»)')
r2 = R(s1, 'R2', '2.2k', 860, 110, 'A12', 'VB')
r3 = R(s1, 'R3', '2.2k', 1040, 110, 'VB', 'GND')
c5 = C(s1, 'C5', '220u', 1200, 160, 'VB', 'GND', polar=True)
s1.note(816, 228, 'Делитель R2/R3 + C5 дают 6 В. Нагрузка на VB — только входы микросхем и разделительные конденсаторы.')

s1.block(20, 260, 760, 330, 'Источник белого шума и усилитель')
r4 = R(s1, 'R4', '1k', 90, 330, 'A12', 'NZ')
c6 = C(s1, 'C6', '100u', 90, 400, 'NZ', 'GND', polar=True)
r5 = R(s1, 'R5', '10k', 230, 330, 'NZ', 'QE')
q1 = s1.NPN('Q1', '2N3904', 330, 360, 180)
conn(s1, q1, E='QE', B='GND', C='GND')
c7 = C(s1, 'C7', '1u', 440, 330, 'QE', 'NIN', v=False)
r6 = R(s1, 'R6', '100k', 530, 400, 'NIN', 'VB', v=True)
u1a = opamp(s1, 'U1', 'A', 'TL072', 640, 340, {'+': 3, '-': 2, 'O': 1}, p='NIN', m='INV1', o='W')
r7 = R(s1, 'R7', '1k', 90, 500, 'INV1', 'GX1')
c8 = C(s1, 'C8', '47u', 220, 500, 'GX1', 'VB', v=False, polar=True)
r8 = R(s1, 'R8', '4.7k', 360, 500, 'W', 'RFM')
rv1 = pot(s1, 'RV1', '100k', 530, 510, 'INV1', 'INV1', 'RFM', trim=True)
s1.note(36, 570, 'Усиление U1A = 1 + (R8 + RV1)/R7: от 6 до 107. RV1 подбирает уровень шума (на выходе W ≈ 100–150 мВ ср.-кв.).')

s1.block(800, 260, 740, 330, 'Фильтр розового шума (−3 дБ/окт.) и усилитель')
r9 = R(s1, 'R9', '18k', 860, 330, 'W', 'PK')
r10 = R(s1, 'R10', '11k', 1020, 330, 'PK', 'P1')
c9 = C(s1, 'C9', '100n', 1160, 330, 'P1', 'VB', v=False)
r11 = R(s1, 'R11', '3.6k', 1020, 400, 'PK', 'P2')
c10 = C(s1, 'C10', '39n', 1160, 400, 'P2', 'VB', v=False)
r12 = R(s1, 'R12', '750', 1020, 470, 'PK', 'P3')
c11 = C(s1, 'C11', '18n', 1160, 470, 'P3', 'VB', v=False)
u1b = opamp(s1, 'U1', 'B', 'TL072', 1360, 400, {'+': 5, '-': 6, 'O': 7}, p='PK', m='INV2', o='PN')
r13 = R(s1, 'R13', '1k', 1250, 520, 'INV2', 'GX2')
c12 = C(s1, 'C12', '47u', 1380, 520, 'GX2', 'VB', v=False, polar=True)
r14 = R(s1, 'R14', '15k', 1360, 470, 'PN', 'INV2')
s1.note(816, 570, 'R9 + три RC-цепи (R10C9, R11C10, R12C11) дают наклон −3 дБ/окт. ±0,3 дБ в диапазоне 30 Гц…16 кГц.')

s1.block(20, 610, 760, 190, 'Питание микросхем U1, U2')
u1p = power_unit(s1, 'U1', 'TL072', 100, 690, 8, 4, 'A12', 'GND')
c13 = C(s1, 'C13', '100n', 220, 690, 'A12', 'GND')
u2p = power_unit(s1, 'U2', 'TL072', 380, 690, 8, 4, 'A12', 'GND')
c14 = C(s1, 'C14', '100n', 500, 690, 'A12', 'GND')
s1.note(36, 780, 'Развязывающие конденсаторы C13, C14 паяются у выводов 8 и 4 микросхем.')

# ===========================================================================
# SHEET 2 — wave generator (random clocked gates -> envelope)
# ===========================================================================
s2 = D.sheet('2-waves', 'Лист 2 · Генератор волн: случайные импульсы → огибающая', 1560, 1020)

s2.block(20, 40, 520, 260, 'Компаратор шума и уровень «Surf»')
r32 = R(s2, 'R32', '91k', 80, 110, 'A12', 'SA')
rv5 = pot(s2, 'RV5', '10k lin', 230, 130, 'SB', 'SURFW', 'SA')
r33 = R(s2, 'R33', '91k', 380, 110, 'SB', 'GND')
c23 = C(s2, 'C23', '10u', 470, 150, 'SURFW', 'GND', polar=True)
rv2 = pot(s2, 'RV2', '10k', 90, 250, 'W', 'WA', 'VB', trim=True)
c36 = C(s2, 'C36', '470n', 230, 250, 'WA', 'ACT', v=False)
r57 = R(s2, 'R55', '100k', 230, 190, 'SURFW', 'ACT', v=False)
u4a = opamp(s2, 'U4', 'A', 'LM358', 420, 240, {'+': 3, '-': 2, 'O': 1}, p='ACT', m='VB', o='CMP')
s2.note(36, 288, 'W через C36 (убирает дрейф), к нему добавляется смещение R55 от Surf: вероятность «1» от 1 % до 99 %. RV2 — масштаб шума.')

s2.block(560, 40, 980, 440, 'Два асимметричных мультивибратора (Tide)')
# osc 1
r34 = R(s2, 'R34', '1M', 640, 110, 'CK1', 'P1P')
r35 = R(s2, 'R35', '1M', 820, 110, 'P1P', 'VB')
u3a = opamp(s2, 'U3', 'A', 'LM324', 1010, 150, {'+': 3, '-': 2, 'O': 1}, p='P1P', m='T1', o='CK1')
c24 = C(s2, 'C24', '4.7u', 1160, 110, 'T1', 'GND', v=False)
d2 = Dio(s2, 'D2', '1N4148', 640, 200, 'CK1', 'H1')
r36 = R(s2, 'R36', '180k', 780, 200, 'H1', 'T1')
r37 = R(s2, 'R37', '390k', 640, 270, 'T1', 'L1')
rv6a = pot(s2, 'RV6A', '1M (Tide A)', 830, 290, 'W1', 'W1', 'L1')
d3 = Dio(s2, 'D3', '1N4148', 950, 270, 'W1', 'CK1')
s2.note(1050, 215, 'T = t_имп(R36·C24) + t_пауз((R37+RV6A)·C24)')
# osc 2
r38 = R(s2, 'R38', '1M', 640, 350, 'CK2', 'P2P')
r39 = R(s2, 'R39', '1M', 820, 350, 'P2P', 'VB')
u3b = opamp(s2, 'U3', 'B', 'LM324', 1010, 390, {'+': 5, '-': 6, 'O': 7}, p='P2P', m='T2', o='CK2')
c25 = C(s2, 'C25', '6.8u', 1160, 350, 'T2', 'GND', v=False)
d4 = Dio(s2, 'D4', '1N4148', 1260, 200, 'CK2', 'H2')
r40 = R(s2, 'R40', '120k', 1400, 200, 'H2', 'T2')
r41 = R(s2, 'R41', '390k', 1260, 270, 'T2', 'L2')
rv6b = pot(s2, 'RV6B', '1M (Tide B)', 1450, 290, 'W2', 'W2', 'L2')
d5 = Dio(s2, 'D5', '1N4148', 1260, 350, 'W2', 'CK2')
s2.note(1050, 440, 'RV6 — сдвоенный потенциометр 1 МОм (линейный), вращение по часовой = чаще.')

s2.block(20, 500, 520, 240, 'Триггеры: бит из шума запоминается по фронту часов')
u5 = s2.BOX('U5', 'CD4013', 280, 640,
            [(1, 'Q1'), (2, 'Q̄1'), (3, 'CLK1'), (4, 'RESET1'), (5, 'D1'), (6, 'SET1'), (7, 'VSS')],
            [(14, 'VDD'), (13, 'Q2'), (12, 'Q̄2'), (11, 'CLK2'), (10, 'RESET2'), (9, 'D2'), (8, 'SET2')], w=130)
conn(s2, u5, **{'1': 'Q1', '2': 'NC', '3': 'CK1', '4': 'GND', '5': 'CMP', '6': 'GND', '7': 'GND',
                '14': 'A12', '13': 'Q2', '12': 'NC', '11': 'CK2', '10': 'GND', '9': 'CMP', '8': 'GND'})
c15 = C(s2, 'C15', '100n', 430, 560, 'A12', 'GND')

s2.block(560, 500, 980, 240, 'Вентили И (CD4081), смешивание и огибающая волны')
u10 = s2.BOX('U9', 'CD4081', 700, 640,
             [(1, 'A'), (2, 'B'), (3, 'J = A·B'), (4, 'K = C·D'), (5, 'C'), (6, 'D'), (7, 'VSS')],
             [(14, 'VDD'), (13, 'H'), (12, 'G'), (11, 'M'), (10, 'L'), (9, 'F'), (8, 'E')], w=120)
conn(s2, u10, **{'1': 'CK1', '2': 'Q1', '3': 'G1', '4': 'G2', '5': 'CK2', '6': 'Q2', '7': 'GND',
                 '14': 'A12', '13': 'GND', '12': 'GND', '11': 'NC', '10': 'NC', '9': 'GND', '8': 'GND'})
c37 = C(s2, 'C37', '100n', 830, 570, 'A12', 'GND')
r44 = R(s2, 'R42', '47k', 960, 570, 'G1', 'T')
r45 = R(s2, 'R43', '100k', 960, 640, 'G2', 'T')
r46 = R(s2, 'R44', '82k', 960, 700, 'T', 'GND')
d6 = Dio(s2, 'D6', '1N4148', 1110, 590, 'T', 'NA')
r47 = R(s2, 'R45', '100k', 1230, 590, 'NA', 'E')
c26 = C(s2, 'C26', '4.7u', 1320, 640, 'E', 'GND', polar=True)
r48 = R(s2, 'R46', '470k', 1390, 640, 'E', 'GND', v=True)
u3c = opamp(s2, 'U3', 'C', 'LM324', 1480, 600, {'+': 10, '-': 9, 'O': 8}, p='E', m='VW', o='VW')
s2.note(576, 728, 'G = 1 только если часы в «1» И бит в «1». Импульс ≈ 1,2 с даёт волну: быстрый подъём, медленный спад.')

s2.block(20, 760, 1520, 240, 'Задержка пены, светодиод волны, питание микросхем')
r49 = R(s2, 'R47', '100k', 80, 840, 'VW', 'FN')
c27 = C(s2, 'C27', '4.7u', 190, 890, 'FN', 'GND', polar=True)
u3d = opamp(s2, 'U3', 'D', 'LM324', 330, 850, {'+': 12, '-': 13, 'O': 14}, p='FN', m='FW', o='FW')
r54 = R(s2, 'R52', '10k', 480, 840, 'VW', 'QB')
r55 = R(s2, 'R53', '10M', 480, 910, 'A12', 'QB')
q2 = s2.NPN('Q2', '2N3904', 620, 860, 0)
conn(s2, q2, B='QB', E='GND', C='LEDK')
d14 = Dio(s2, 'D10', 'LED aqua', 760, 840, 'LEDA', 'LEDK', led=True)
r56 = R(s2, 'R54', '820', 880, 840, 'V12', 'LEDA')
u3p = power_unit(s2, 'U3', 'LM324', 1060, 890, 4, 11, 'A12', 'GND')
c28 = C(s2, 'C28', '100n', 1180, 890, 'A12', 'GND')
u4b = opamp(s2, 'U4', 'B', 'LM358', 1330, 870, {'+': 5, '-': 6, 'O': 7}, p='VB', m='SPARE', o='SPARE')
u4p = power_unit(s2, 'U4', 'LM358', 1450, 890, 8, 4, 'A12', 'GND')
c29 = C(s2, 'C29', '100n', 1500, 960, 'A12', 'GND', v=False)
s2.note(500, 975, 'LED слабо тлеет при включении и ярко вспыхивает на гребне волны.')

# ===========================================================================
# SHEET 3 — audio engine: filter + VCAs on LM13700, mixer
# ===========================================================================
s3 = D.sheet('3-audio', 'Лист 3 · Звуковой тракт: фильтр и усилители на LM13700, смеситель', 1560, 1060)

s3.block(20, 40, 760, 470, 'Основной слой волны: ФНЧ (U6A) → усилитель (U6B)')
r15 = R(s3, 'R15', '100k', 80, 110, 'PN', 'VP1')
r16 = R(s3, 'R16', '1k', 240, 110, 'VP1', 'VB')
r17 = R(s3, 'R17', '100k', 80, 180, 'VCFO', 'VM1')
r18 = R(s3, 'R18', '1k', 240, 180, 'VM1', 'VB')
c16 = C(s3, 'C16', '2.2n', 80, 250, 'VCFN', 'VB', v=False)
r19 = R(s3, 'R19', '10k', 240, 250, 'VCFO', 'GND')
r20 = R(s3, 'R20', '100k', 80, 330, 'VCFO', 'VP2')
r21 = R(s3, 'R21', '1k', 240, 330, 'VP2', 'VB')
r22 = R(s3, 'R22', '1k', 80, 400, 'VM2', 'VB')
u6 = s3.BOX('U6', 'LM13700', 560, 270,
            [(1, 'Iabc A'), (2, 'Dbias A'), (3, 'IN+ A'), (4, 'IN− A'), (5, 'OUT A'), (6, 'V−'), (7, 'BUF IN A'), (8, 'BUF OUT A')],
            [(16, 'Iabc B'), (15, 'Dbias B'), (14, 'IN+ B'), (13, 'IN− B'), (12, 'OUT B'), (11, 'V+'), (10, 'BUF IN B'), (9, 'BUF OUT B')], w=130)
conn(s3, u6, **{'1': 'IC1', '2': 'NC', '3': 'VP1', '4': 'VM1', '5': 'VCFN', '6': 'GND', '7': 'VCFN', '8': 'VCFO',
                '16': 'IC2', '15': 'NC', '14': 'VP2', '13': 'VM2', '12': 'MIX', '11': 'A12', '10': 'GND', '9': 'NC'})
s3.note(36, 500, 'U6A: фильтр нижних частот 1-го порядка, частота среза ∝ ток Iabc. U6B: усилитель, коэффициент ∝ ток Iabc.')

s3.block(800, 40, 740, 470, 'Слой пены: шум → ФВЧ → усилитель (U7A)')
c17 = C(s3, 'C17', '4.7n', 870, 110, 'W', 'FIN', v=False)
r23 = R(s3, 'R23', '10k', 1030, 110, 'FIN', 'VB')
r24 = R(s3, 'R24', '100k', 870, 180, 'FIN', 'VP3')
r25 = R(s3, 'R25', '1k', 1030, 180, 'VP3', 'VB')
r26 = R(s3, 'R26', '1k', 870, 250, 'VM3', 'VB')
u7 = s3.BOX('U7', 'LM13700', 1330, 270,
            [(1, 'Iabc A'), (2, 'Dbias A'), (3, 'IN+ A'), (4, 'IN− A'), (5, 'OUT A'), (6, 'V−'), (7, 'BUF IN A'), (8, 'BUF OUT A')],
            [(16, 'Iabc B'), (15, 'Dbias B'), (14, 'IN+ B'), (13, 'IN− B'), (12, 'OUT B'), (11, 'V+'), (10, 'BUF IN B'), (9, 'BUF OUT B')], w=130)
conn(s3, u7, **{'1': 'IC3', '2': 'NC', '3': 'VP3', '4': 'VM3', '5': 'MIX', '6': 'GND', '7': 'GND', '8': 'NC',
                '16': 'GND', '15': 'NC', '14': 'VB', '13': 'VB', '12': 'NC', '11': 'A12', '10': 'GND', '9': 'NC'})
s3.note(816, 500, 'Вторая половина U7 не используется: входы на VB, Iabc на землю.')

s3.block(20, 530, 760, 250, 'Токи управления Iabc (Tone, волна, фон)')
r31 = R(s3, 'R31', '220k', 80, 600, 'TONW', 'IC1')
d11 = Dio(s3, 'D7', '1N4148', 80, 670, 'VW', 'V1')
r50 = R(s3, 'R48', '18k', 240, 670, 'V1', 'IC1')
d12 = Dio(s3, 'D8', '1N4148', 400, 600, 'VW', 'V2')
r51 = R(s3, 'R49', '11k', 560, 600, 'V2', 'IC2')
r52 = R(s3, 'R50', '470k', 400, 670, 'A12', 'IC2')
d13 = Dio(s3, 'D9', '1N4148', 560, 670, 'FW', 'V3')
r53 = R(s3, 'R51', '39k', 700, 670, 'V3', 'IC3')
s3.note(36, 770, 'Диоды отсекают «мёртвую зону», когда напряжение волны VW ниже ≈1,8 В; R50 — тихий фон между волнами.')

s3.block(800, 530, 740, 250, 'Смеситель (U2A)')
u2a = opamp(s3, 'U2', 'A', 'TL072', 940, 650, {'+': 3, '-': 2, 'O': 1}, p='VB', m='MIX', o='MO')
r27 = R(s3, 'R27', '15k', 1090, 620, 'MO', 'MIX')
c18 = C(s3, 'C18', '100p', 1090, 690, 'MO', 'MIX', v=False)
u2b = opamp(s3, 'U2', 'B', 'TL072', 1340, 650, {'+': 5, '-': 6, 'O': 7}, p='VB', m='SPARE2', o='SPARE2')
s3.note(816, 770, 'U2A — преобразует токи OTA в напряжение. U2B не используется (повторитель на VB).')

s3.block(20, 800, 1520, 240, 'Тон (Tone), блокировка и развязка питания')
r29 = R(s3, 'R29', '27k', 80, 880, 'A12', 'TOPT')
rv3 = pot(s3, 'RV3', '100k lin', 240, 900, 'BOTT', 'TONW', 'TOPT')
r30 = R(s3, 'R30', '30k', 400, 880, 'BOTT', 'GND')
c22 = C(s3, 'C22', '100n', 500, 930, 'TONW', 'GND')
c19 = C(s3, 'C19', '100n', 700, 930, 'A12', 'GND')
u6p = power_unit(s3, 'U6', 'LM13700', 880, 920, 11, 6, 'A12', 'GND')
u7p = power_unit(s3, 'U7', 'LM13700', 1100, 920, 11, 6, 'A12', 'GND')
c20 = C(s3, 'C20', '100n', 1240, 930, 'A12', 'GND')
c21 = C(s3, 'C21', '100n', 1340, 930, 'A12', 'GND')
s3.note(36, 1030, 'Tone задаёт базовый ток фильтра 5…40 мкА (срез ≈ 70…550 Гц); волна поднимает срез до ≈ 3,5 кГц.')

# ===========================================================================
# SHEET 4 — volume + power amplifier
# ===========================================================================
s4 = D.sheet('4-amp', 'Лист 4 · Громкость и усилитель мощности', 1560, 560)

s4.block(20, 40, 760, 250, 'Регулятор громкости')
c30 = C(s4, 'C30', '4.7u', 100, 120, 'MO', 'VOLH', v=False, polar=True)
rv4 = pot(s4, 'RV4', '10k log', 280, 140, 'GND', 'VOLW', 'VOLH')
s4.note(36, 280, 'Конденсатор C30 отсекает постоянную составляющую 6 В; вывод «+» к MO.')

s4.block(800, 40, 740, 480, 'Усилитель мощности LM386 (усиление ×20)')
u8 = s4.BOX('U8', 'LM386', 1000, 230,
            [(1, 'GAIN'), (2, '−IN'), (3, '+IN'), (4, 'GND')],
            [(8, 'GAIN'), (7, 'BYPASS'), (6, 'Vs'), (5, 'OUT')], w=120)
conn(s4, u8, **{'1': 'NC', '2': 'GND', '3': 'VOLW', '4': 'GND', '8': 'NC', '7': 'BYP', '6': 'V12', '5': 'OUTA'})
c31 = C(s4, 'C31', '10u', 1180, 280, 'BYP', 'GND', polar=True)
c32 = C(s4, 'C32', '100u', 1280, 160, 'V12', 'GND', polar=True)
c33 = C(s4, 'C33', '100n', 1380, 160, 'V12', 'GND')
c34 = C(s4, 'C34', '220u', 1180, 360, 'OUTA', 'SPK', v=False, polar=True)
spk1 = speaker(s4, 'SPK1', 1400, 380)
conn(s4, spk1, **{'1': 'SPK', '2': 'GND'})
r28 = R(s4, 'R28', '10', 1080, 440, 'OUTA', 'ZOB')
c35 = C(s4, 'C35', '47n', 1220, 440, 'ZOB', 'GND', v=False)
s4.note(816, 508, 'R28+C35 — цепочка Цобеля, гасит самовозбуждение. Выводы 1 и 8 свободны: усиление 20.')
s4.note(816, 496, 'Для усиления ×200 можно добавить конденсатор 10 мкФ между выводами 1 и 8 (необязательно, в список деталей не входит).')
