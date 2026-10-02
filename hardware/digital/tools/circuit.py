"""Surf Synth, digital version: Raspberry Pi Pico 2 + MCP3008 (pots) + MAX98357A (I2S amplifier).

The schematic is the single source of truth: build.py derives the netlist, the wiring table,
the parts list and the 3D data from the drawing below.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'lib'))
from schematic import Design, rot, INK, SOFT, ACCENT

RAILS = {'V5', 'V3', 'VSYS'}
D = Design()


def outward(part, pin):
    lx, ly = part.local_pins[pin]
    if part.kind == 'IC' or abs(lx) >= abs(ly):
        d = (1 if lx > 0 else -1, 0)
    else:
        d = (0, 1 if ly > 0 else -1)
    return rot(d, part.rot)


def at(sh, part, pin, net):
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
    elif part.kind == 'POT' and pin == 'W':
        sh.label(net, x, y, side='l')
    else:
        sh.label(net, x, y, side='r' if ox >= 0 else 'l')


def nc(sh, part, pin):
    x, y = part.pin_xy[pin]
    sh.svg_items.append(f'<g stroke="{SOFT}" stroke-width="1.2"><line x1="{x-4}" y1="{y-4}" x2="{x+4}" y2="{y+4}"/><line x1="{x-4}" y1="{y+4}" x2="{x+4}" y2="{y-4}"/></g>')
    sh.nc_pins = getattr(sh, 'nc_pins', []) + [(part.ref, pin)]


def conn(sh, part, **nets):
    for pin, net in nets.items():
        if net == 'NC': nc(sh, part, pin)
        else: at(sh, part, pin, net)
    return part


def R(sh, ref, val, x, y, a, b, v=False):
    return conn(sh, sh.R(ref, val, x, y, 90 if v else 0), **{'1': a, '2': b})


def C(sh, ref, val, x, y, a, b, v=True, polar=False):
    return conn(sh, sh.C(ref, val, x, y, 90 if v else 0, polar=polar), **{'1': a, '2': b})


def jack(sh, ref, x, y):
    svg = ('<rect x="-34" y="-18" width="26" height="36" rx="3" fill="none"/>'
           '<line x1="-8" y1="-10" x2="20" y2="-10"/><line x1="-8" y1="10" x2="20" y2="10"/>'
           '<circle cx="-21" cy="0" r="7"/><circle cx="-21" cy="0" r="2" fill="#2b3033"/>')
    p = sh.custom(ref, 'JACK', 'DC 5.5/2.1', x, y, {'TIP': (20, -10), 'SLV': (20, 10)}, svg, {}, None)
    sh.text(x - 21, y - 24, ref, size=10, weight=700, anchor='middle')
    sh.text(x - 21, y + 34, 'гнездо питания', size=8.5, anchor='middle', fill=SOFT)
    sh.text(x - 21, y + 45, '5,5 × 2,1 мм, центр «+»', size=8.5, anchor='middle', fill=SOFT)
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
    sh.text(x + 4, y + 32, 'динамик 8 Ом', size=8.5, anchor='middle', fill=SOFT)
    return p


# ===========================================================================
# SHEET 1 — power, Pico 2, I2S amplifier, speaker, LED
# ===========================================================================
s1 = D.sheet('1-main', 'Лист 1 · Питание, Raspberry Pi Pico 2, усилитель, динамик, светодиод', 1500, 800)

s1.block(20, 40, 640, 190, 'Питание 5 В')
j1 = jack(s1, 'J1', 80, 120)
sw1 = switch(s1, 'SW1', 'кнопка с фикс.', 190, 110)
s1.wire(j1.pin_xy['TIP'], (140, 110)); s1.wire((140, 110), sw1.pin_xy['1']); s1.label('V5IN', 140, 110, side='r')
at(s1, j1, 'SLV', 'GND')
at(s1, sw1, '2', 'V5')
d1 = s1.D('D1', '1N5819', 330, 120)
conn(s1, d1, A='V5', K='VSYS')
c1 = C(s1, 'C1', '470u', 460, 150, 'V5', 'GND', polar=True)
s1.note(36, 216, 'Кнопка включает питание всего устройства. D1 не даёт 5 В уйти обратно в USB, когда Pico подключена к компьютеру.')

s1.block(20, 250, 640, 520, 'Raspberry Pi Pico 2 (вид сверху: USB наверху, выводы 1–20 слева, 21–40 справа)')
u1 = s1.BOX('U1', 'Raspberry Pi Pico 2', 340, 500,
            [(12, 'GP9'), (14, 'GP10'), (15, 'GP11'), (20, 'GP15')],
            [(21, 'GP16'), (22, 'GP17'), (24, 'GP18'), (25, 'GP19'), (33, 'AGND'), (35, 'ADC_VREF'), (36, '3V3 (OUT)'), (38, 'GND'), (39, 'VSYS')], w=180, spacing=28)
conn(s1, u1, **{'12': 'I2S_DIN', '14': 'I2S_BCLK', '15': 'I2S_LRC', '20': 'LED_CTL',
                '21': 'SPI_MISO', '22': 'SPI_CS', '24': 'SPI_SCK', '25': 'SPI_MOSI', '33': 'GND', '35': 'NC', '36': 'V3', '38': 'GND', '39': 'VSYS'})
s1.note(36, 760, 'Остальные выводы Pico не используются. Нумерация — физические номера выводов платы.')

s1.block(680, 40, 800, 330, 'Усилитель MAX98357A и динамик')
u3 = s1.BOX('U3', 'MAX98357A (модуль)', 900, 200,
            [(1, 'VIN'), (2, 'GND'), (3, 'SD'), (4, 'GAIN'), (5, 'DIN'), (6, 'BCLK'), (7, 'LRC')],
            [(8, 'OUT +'), (9, 'OUT −')], w=170, spacing=28)
conn(s1, u3, **{'1': 'V5', '2': 'GND', '3': 'NC', '4': 'NC', '5': 'I2S_DIN', '6': 'I2S_BCLK', '7': 'I2S_LRC', '8': 'SPK_P', '9': 'SPK_N'})
spk1 = speaker(s1, 'SPK1', 1220, 200)
conn(s1, spk1, **{'1': 'SPK_P', '2': 'SPK_N'})
s1.note(700, 350, 'SD и GAIN не подключаются: усилитель всегда включён, усиление 9 дБ. Звук идёт в оба канала одинаково.')

s1.block(680, 390, 800, 380, 'Светодиод волны')
r1 = R(s1, 'R1', '4.7k', 780, 470, 'LED_CTL', 'QB')
q1 = s1.NPN('Q1', 'BC547B', 980, 490, 0)
conn(s1, q1, B='QB', E='GND', C='QC')
d2 = s1.D('D2', 'GNL-3014BGC', 1160, 470, 0, led=True)
conn(s1, d2, A='LEDA', K='QC')
r2 = R(s1, 'R2', '180', 1320, 470, 'V5', 'LEDA')
s1.note(700, 560, 'Pico (3,3 В) не может зажечь бирюзовый светодиод напрямую (ему нужно около 3 В и 10 мА), поэтому он включается транзистором от 5 В.')

# ===========================================================================
# SHEET 2 — potentiometers and the ADC
# ===========================================================================
s2 = D.sheet('2-controls', 'Лист 2 · Ручки: потенциометры и АЦП MCP3008', 1500, 700)

s2.block(20, 40, 560, 640, 'АЦП MCP3008 (DIP-16, в панельке)')
u2 = s2.BOX('U2', 'MCP3008', 300, 300,
            [(1, 'CH0'), (2, 'CH1'), (3, 'CH2'), (4, 'CH3'), (5, 'CH4'), (6, 'CH5'), (7, 'CH6'), (8, 'CH7')],
            [(16, 'VDD'), (15, 'VREF'), (14, 'AGND'), (13, 'CLK'), (12, 'DOUT'), (11, 'DIN'), (10, 'CS/SHDN'), (9, 'DGND')], w=150, spacing=34)
conn(s2, u2, **{'1': 'ADC0', '2': 'ADC1', '3': 'ADC2', '4': 'ADC3', '5': 'GND', '6': 'GND', '7': 'GND', '8': 'GND',
                '16': 'V3', '15': 'V3', '14': 'GND', '13': 'SPI_SCK', '12': 'SPI_MISO', '11': 'SPI_MOSI', '10': 'SPI_CS', '9': 'GND'})
c3 = C(s2, 'C3', '100n', 470, 560, 'V3', 'GND')
c2 = C(s2, 'C2', '10u', 530, 560, 'V3', 'GND', polar=True)
s2.note(36, 660, 'Неиспользуемые входы CH4–CH7 соединены с землёй, чтобы не ловили наводки.')

s2.block(600, 40, 880, 640, 'Потенциометры 10 кОм (на лицевой панели), по 3 провода к плате')
pots = [('RV1', 'Surf', 'ADC0'), ('RV2', 'Tide', 'ADC1'), ('RV3', 'Tone', 'ADC2'), ('RV4', 'Volume', 'ADC3')]
for i, (ref, name, adc) in enumerate(pots):
    y = 130 + i * 140
    rv = s2.POT(ref, '10k', 760, y, 0)
    conn(s2, rv, **{'1': 'GND', 'W': adc, '3': 'V3'})
    cap = C(s2, f'C{4+i}', '100n', 960, y, adc, 'GND', v=True)
    s2.text(660, y + 4, name, size=13, weight=700)
    s2.text(1060, y - 6, 'вывод 1 → земля, вывод 3 → 3,3 В', size=9.5, fill=SOFT)
    s2.text(1060, y + 8, 'движок → вход АЦП, 100 нФ гасит дребезг', size=9.5, fill=SOFT)
s2.note(616, 668, 'Если ручка вращается «наоборот», поменяйте местами крайние выводы 1 и 3 потенциометра.')
