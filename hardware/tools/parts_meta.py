"""Physical description of every part: BOM text, package, size for the 3D view, KiCad footprint."""
import re

E_COL = ['black', 'brown', 'red', 'orange', 'yellow', 'green', 'blue', 'violet', 'grey', 'white']

def ohms(v):
    v = str(v).split()[0]
    m = re.match(r'^([0-9.]+)([kM]?)$', v)
    return float(m.group(1)) * {'': 1, 'k': 1e3, 'M': 1e6}[m.group(2)]

def fmt_ohm(v):
    x = ohms(v)
    def n(a): return ('%g' % a).replace('.', ',')
    if x >= 1e6: return n(x / 1e6) + ' МОм'
    if x >= 1e3: return n(x / 1e3) + ' кОм'
    return n(x) + ' Ом'

def fmt_cap(v):
    m = re.match(r'^([0-9.]+)([pnu])$', str(v))
    a, u = m.group(1), m.group(2)
    return a.replace('.', ',') + ' ' + {'p': 'пФ', 'n': 'нФ', 'u': 'мкФ'}[u]

def cap_farads(v):
    m = re.match(r'^([0-9.]+)([pnu])$', str(v))
    return float(m.group(1)) * {'p': 1e-12, 'n': 1e-9, 'u': 1e-6}[m.group(2)]

def resistor_bands(v):
    """5-band colour code (1 %): d1 d2 d3 multiplier tolerance(brown)."""
    x = ohms(v)
    # represent as 3 significant digits
    exp = 0
    while x >= 1000: x /= 10; exp += 1
    while x < 100: x *= 10; exp -= 1
    d = int(round(x))
    if d >= 1000: d //= 10; exp += 1
    digits = [d // 100, (d // 10) % 10, d % 10]
    mult = {-2: 'silver', -1: 'gold'}.get(exp, None) or E_COL[exp] if exp >= 0 else {-2: 'silver', -1: 'gold'}[exp]
    return [E_COL[digits[0]], E_COL[digits[1]], E_COL[digits[2]], mult, 'brown']

# --- footprints (mm): w, d (board plane), h (height above board) ----------------
FP = {
    'R':        dict(w=4.4, d=3.6, h=8.0, kicad='Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical'),
    'C_disc':   dict(w=5.8, d=3.0, h=5.5, kicad='Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm'),
    'C_film_s': dict(w=7.8, d=3.6, h=7.0, kicad='Capacitor_THT:C_Rect_L7.2mm_W3.5mm_P5.00mm'),
    'C_film_m': dict(w=11.0, d=5.0, h=10.0, kicad='Capacitor_THT:C_Rect_L10.3mm_W4.5mm_P7.50mm_MKS4'),
    'C_film_l': dict(w=14.0, d=6.0, h=11.0, kicad='Capacitor_THT:C_Rect_L13.0mm_W6.0mm_P10.00mm'),
    'C_film_xl':dict(w=27.0, d=9.0, h=19.0, kicad='Capacitor_THT:C_Rect_L26.5mm_W9.5mm_P22.50mm'),
    'C_el5':    dict(w=6.0, d=6.0, h=11.5, kicad='Capacitor_THT:CP_Radial_D5.0mm_P2.00mm'),
    'C_el63':   dict(w=7.3, d=7.3, h=11.5, kicad='Capacitor_THT:CP_Radial_D6.3mm_P2.50mm'),
    'C_el8':    dict(w=9.0, d=9.0, h=12.0, kicad='Capacitor_THT:CP_Radial_D8.0mm_P3.50mm'),
    'D':        dict(w=4.0, d=3.6, h=8.0, kicad='Diode_THT:D_DO-35_SOD27_P2.54mm_Vertical_KathodeUp'),
    'D41':      dict(w=5.4, d=4.4, h=8.5, kicad='Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal'),
    'TO92':     dict(w=5.6, d=4.6, h=5.2, kicad='Package_TO_SOT_THT:TO-92_Inline'),
    'DIP8':     dict(w=10.8, d=9.4, h=8.6, kicad='Package_DIP:DIP-8_W7.62mm_Socket'),
    'DIP14':    dict(w=19.2, d=9.4, h=8.6, kicad='Package_DIP:DIP-14_W7.62mm_Socket'),
    'DIP16':    dict(w=21.8, d=9.4, h=8.6, kicad='Package_DIP:DIP-16_W7.62mm_Socket'),
    'TRIM':     dict(w=10.2, d=5.2, h=10.0, kicad='Potentiometer_THT:Potentiometer_Bourns_3386P_Vertical'),
    'POT9':     dict(w=10.0, d=7.0, h=14.0, kicad='Potentiometer_THT:Potentiometer_Alpha_RD901F-40-00D_Single_Vertical'),
    'POT9D':    dict(w=10.0, d=7.0, h=14.0, kicad='Potentiometer_THT:Potentiometer_Alpha_RD902F-40-00D_Dual_Vertical'),
    'POT16':    dict(w=10.0, d=7.0, h=14.0, kicad='Potentiometer_THT:Potentiometer_Alps_RK09K_Single_Vertical'),
    'JACK':     dict(w=14.5, d=9.0, h=11.0, kicad='Connector_BarrelJack:BarrelJack_Horizontal'),
    'SW':       dict(w=13.0, d=13.0, h=10.0, kicad='Button_Switch_THT:SW_PUSH_12mm'),
    'LED':      dict(w=3.6, d=3.6, h=6.0, kicad='LED_THT:LED_D3.0mm'),
    'SPK':      dict(w=3.0, d=3.0, h=1.0, kicad='Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical'),
}

def ic_package(value):
    return {'TL072': 'DIP8', 'LM358': 'DIP8', 'LM386': 'DIP8', 'LM324': 'DIP14', 'CD4013': 'DIP14', 'CD4081': 'DIP14', 'LM13700': 'DIP16'}[value]

IC_NOTES = {
    'TL072': ('Сдвоенный малошумящий ОУ с полевыми входами', 'TL072CP / TL072ACP, DIP-8'),
    'LM358': ('Сдвоенный ОУ, работает от одного питания, выход до «земли»', 'LM358N, DIP-8'),
    'LM324': ('Счетверённый ОУ, один источник питания', 'LM324N, DIP-14'),
    'CD4013': ('Два D-триггера (КМОП)', 'CD4013BE, DIP-14'),
    'CD4081': ('Четыре элемента 2И (КМОП)', 'CD4081BE, DIP-14'),
    'LM13700': ('Сдвоенный транскондактансный ОУ (OTA) с буферами', 'LM13700N, DIP-16'),
    'LM386': ('Усилитель мощности НЧ, напряжение питания до 15–18 В', 'LM386N-3 или LM386N-4 (не N-1: он рассчитан на 12 В максимум), DIP-8'),
}

POTS = {
    'RV1': ('Подстроечный резистор 100 кОм', 'многооборотный 3386P / 3296W, вертикальный', 'TRIM', 'Усиление источника шума (калибровка)'),
    'RV2': ('Подстроечный резистор 10 кОм', 'многооборотный 3386P / 3296W, вертикальный', 'TRIM', 'Масштаб шума на компараторе (калибровка)'),
    'RV3': ('Потенциометр 100 кОм линейный (B100K)', 'Alpha 9 мм, вал 6 мм, на плату', 'POT9', 'Ручка Tone'),
    'RV4': ('Потенциометр 10 кОм логарифмический (A10K)', 'Alpha 9 мм, вал 6 мм, на плату', 'POT9', 'Ручка Volume'),
    'RV5': ('Потенциометр 10 кОм линейный (B10K)', 'Alpha 16 мм или 9 мм, вал 6 мм, на плату', 'POT16', 'Ручка Surf'),
    'RV6A': ('Сдвоенный потенциометр 1 МОм линейный (B1M), секция A', 'Alpha 9 мм сдвоенный, вал 6 мм, на плату', 'POT9D', 'Ручка Tide (секция A)'),
    'RV6B': ('Сдвоенный потенциометр 1 МОм линейный (B1M), секция B', 'тот же корпус, что RV6A', 'POT9D', 'Ручка Tide (секция B)'),
}

RAIL_V = {'V12': 11.8, 'A12': 11.6, 'NZ': 11.3, 'QE': 7.4}

def cap_info(ref, value, polar, pin_nets):
    f = cap_farads(value)
    vmax = max([RAIL_V.get(n, 0) for n in pin_nets] + [6.0])
    if polar:
        v = 25 if vmax > 8 else 16
        if f >= 200e-6 and v == 25: fp = 'C_el8'
        elif f >= 99e-6: fp = 'C_el63'
        else: fp = 'C_el5'
        return (f'Электролитический конденсатор {fmt_cap(value)}, {v} В', f'радиальный, ø{ {"C_el5":5,"C_el63":6.3,"C_el8":8}[fp] } мм', fp, 'polar')
    if ref in ('C24', 'C25'):
        return (f'Плёночный конденсатор {fmt_cap(value)}, 63 В (MKT/MKS)', 'шаг выводов 22,5 мм, крупный', 'C_film_xl', 'film')
    if ref in ('C36',):
        return (f'Плёночный конденсатор {fmt_cap(value)}, 63 В (MKT)', 'шаг выводов 7,5 мм', 'C_film_m', 'film')
    if ref in ('C7',):
        return (f'Плёночный конденсатор {fmt_cap(value)}, 63 В (MKT)', 'шаг выводов 7,5–10 мм', 'C_film_l', 'film')
    if ref in ('C9', 'C10', 'C11', 'C16', 'C17', 'C35'):
        return (f'Плёночный или C0G конденсатор {fmt_cap(value)}, ±5 %, 63 В', 'шаг выводов 5 мм', 'C_film_s', 'film')
    if ref == 'C18':
        return (f'Керамический конденсатор C0G/NP0 {fmt_cap(value)}, 50 В', 'шаг выводов 5 мм', 'C_disc', 'ceramic')
    return (f'Керамический конденсатор X7R {fmt_cap(value)}, 50 В', 'шаг выводов 5 мм', 'C_disc', 'ceramic')

def describe(part, pin_nets):
    k, v, ref = part.kind, part.value, part.ref
    if k == 'R':
        return dict(group='Резисторы', desc=f'Резистор {fmt_ohm(v)}, 0,25 Вт, 1 %', pkg='выводной, ставится стоя', fp='R', bands=resistor_bands(v), vtxt=fmt_ohm(v), type='R')
    if k in ('C', 'CP'):
        d, pkg, fp, sub = cap_info(ref, v, k == 'CP', pin_nets)
        return dict(group='Конденсаторы', desc=d, pkg=pkg, fp=fp, vtxt=fmt_cap(v), type='C', sub=sub)
    if k == 'D':
        if v == '1N5819':
            return dict(group='Диоды', desc='Диод Шоттки 1N5819 (1 А, 40 В)', pkg='DO-41', fp='D41', vtxt='1N5819', type='D')
        return dict(group='Диоды', desc='Диод 1N4148 (кремниевый, быстрый)', pkg='DO-35', fp='D', vtxt='1N4148', type='D')
    if k == 'LED':
        return dict(group='Диоды', desc='Светодиод 3 мм, цвет «аква» (бирюзовый, 495–505 нм)', pkg='3 мм, на лицевой стороне платы', fp='LED', vtxt='LED', type='LED')
    if k == 'NPN':
        if ref == 'Q1':
            return dict(group='Транзисторы', desc='Транзистор 2N3904 — источник шума (используется переход эмиттер-база в обратном включении); подберите экземпляр с хорошим шумом', pkg='TO-92', fp='TO92', vtxt='2N3904', type='Q')
        return dict(group='Транзисторы', desc='Транзистор 2N3904 — драйвер светодиода', pkg='TO-92', fp='TO92', vtxt='2N3904', type='Q')
    if k == 'IC':
        d, mpn = IC_NOTES[v]
        pk = ic_package(v)
        return dict(group='Микросхемы', desc=f'{v}: {d}', pkg=mpn, fp=pk, vtxt=v, type='IC')
    if k == 'POT':
        d, pkg, fp, role = POTS[ref]
        return dict(group='Регуляторы', desc=d, pkg=pkg, fp=fp, vtxt=v, type='POT', role=role)
    if k == 'JACK':
        return dict(group='Разъёмы и коммутация', desc='Гнездо питания DC 5,5 × 2,1 мм (центр «+»)', pkg='на плату или на корпус', fp='JACK', vtxt='DC jack', type='J')
    if k == 'SW':
        return dict(group='Разъёмы и коммутация', desc='Кнопка с фиксацией, SPST, 12 × 12 мм (напр. PBS-110 / «ключ» на лицевую панель)', pkg='на плату, с лицевой стороны', fp='SW', vtxt='SW', type='SW')
    if k == 'SPK':
        return dict(group='Разъёмы и коммутация', desc='Динамик 8 Ом, 1–2 Вт, ø66 мм (2,5″)', pkg='крепится к лицевой панели, 2 провода на плату', fp='SPK', vtxt='8 Ом', type='SPK')
    return None   # opamp units and power units are part of an IC

EXTRA_BOM = [
    ('Печатная плата', 'Двусторонняя, ≈ 104 × 94 мм (разводить по этой схеме; трассировка в комплект не входит)', '1'),
    ('Панелька DIP-8', 'Для U1, U2, U4, U8', '4'),
    ('Панелька DIP-14', 'Для U3, U5, U9', '3'),
    ('Панелька DIP-16', 'Для U6, U7', '2'),
    ('Ручка ø25 мм (на вал 6 мм)', 'Surf, бирюзовая вставка', '1'),
    ('Ручка ø12 мм (на вал 6 мм)', 'Tide, Tone, Volume', '3'),
    ('Блок питания 12 В, ≥ 500 мА', 'Штекер 5,5 × 2,1 мм, центр «+», стабилизированный или хороший импульсный', '1'),
    ('Корпус', 'Задняя часть корпуса и лицевая панель ≈ 192 × 101 × 39 мм, отверстия под ручки, кнопку, светодиод, динамик; крышка снимается с обратной стороны', '1'),
    ('Стойки для платы M3 × 8 мм', 'Плата крепится к лицевой панели', '4'),
    ('Монтажный провод 0,25 мм²', 'Динамик, при необходимости светодиод/гнездо', '≈ 1 м'),
]
