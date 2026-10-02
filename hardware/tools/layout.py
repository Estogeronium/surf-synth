"""Concept placement of parts on the rear side of the board (not a routed PCB).

Coordinates: millimetres, device centre = (0, 0), x to the right and y up as seen
from the FRONT of the device. Panel controls (pots, key, LED) are mounted on the
front side of the board and soldered from the rear, so only their pads are
obstacles here.
"""
import numpy as np

UNIT = 26.0                                  # mm per scene unit of the 3D model
BOARD = dict(x0=-13.0, x1=91.0, y0=-47.0, y1=47.0)

PANEL = {   # centres of the controls in the front view (mm)
    'RV5': (1.5 * UNIT, 0.75 * UNIT),
    'RV6': (0.5 * UNIT, -1.1 * UNIT),
    'RV3': (1.5 * UNIT, -1.1 * UNIT),
    'RV4': (2.5 * UNIT, -1.1 * UNIT),
    'SW1': (3.1 * UNIT, 1.55 * UNIT),
    'D10': (2.65 * UNIT, 1.55 * UNIT),
}

# fixed pad areas on the board: (cx, cy, w, d)
FIXED = {
    'RV5': (PANEL['RV5'][0], PANEL['RV5'][1] - 9.5, 14, 4),
    'RV3': (PANEL['RV3'][0], PANEL['RV3'][1] - 7.5, 10, 4),
    'RV4': (PANEL['RV4'][0], PANEL['RV4'][1] - 7.5, 10, 4),
    'RV6': (PANEL['RV6'][0], PANEL['RV6'][1] - 9.0, 12, 9),
    'SW1': (PANEL['SW1'][0], PANEL['SW1'][1], 13, 13),
    'D10': (PANEL['D10'][0], PANEL['D10'][1], 5, 5),
}
J1_POS = (BOARD['x1'] - 7.5, -2.0)

# target centre of each functional block (sheet-block title -> (x, y))
TARGETS = {
    'Питание 12 В': (66, -10),
    'Средняя точка VB ≈ 6 В (искусственная «земля»)': (50, -40),
    'Источник белого шума и усилитель': (-1, 33),
    'Фильтр розового шума (−3 дБ/окт.) и усилитель': (30, 36),
    'Питание микросхем U1, U2': (12, 38),
    'Компаратор шума и уровень «Surf»': (68, 6),
    'Два асимметричных мультивибратора (Tide)': (46, 8),
    'Триггеры: бит из шума запоминается по фронту часов': (20, 8),
    'Вентили И (CD4081), смешивание и огибающая волны': (10, -6),
    'Задержка пены, светодиод волны, питание микросхем': (-4, -4),
    'Основной слой волны: ФНЧ (U6A) → усилитель (U6B)': (0, 17),
    'Слой пены: шум → ФВЧ → усилитель (U7A)': (20, 20),
    'Токи управления Iabc (Tone, волна, фон)': (-2, -18),
    'Смеситель (U2A)': (26, -44),
    'Тон (Tone), блокировка и развязка питания': (16, -44),
    'Регулятор громкости': (62, -44),
    'Усилитель мощности LM386 (усиление ×20)': (80, -30),
}

NEAR = {'C13': 'U1', 'C14': 'U2', 'C28': 'U3', 'C29': 'U4', 'C15': 'U5', 'C37': 'U9', 'C20': 'U6', 'C21': 'U7',
        'C19': 'U6', 'C32': 'U8', 'C33': 'U8', 'C31': 'U8', 'C34': 'U8', 'C35': 'U8', 'R28': 'U8',
        'R54': 'D10', 'C23': 'RV5', 'C22': 'RV3'}

RES = 1.0   # grid step, mm


def place(items, near_override=None):
    """items: list of dict(ref, w, d, block, area). Returns {ref: (x, y)} (centres)."""
    gx0, gx1, gy0, gy1 = BOARD['x0'], BOARD['x1'], BOARD['y0'], BOARD['y1']
    W, H = int(round((gx1 - gx0) / RES)), int(round((gy1 - gy0) / RES))
    occ = np.zeros((H, W), dtype=bool)

    def to_cell(x, y): return (x - gx0) / RES, (y - gy0) / RES

    def block_area(cx, cy, w, d, mark=True):
        x0 = int(np.floor((cx - w / 2 - gx0) / RES)); x1 = int(np.ceil((cx + w / 2 - gx0) / RES))
        y0 = int(np.floor((cy - d / 2 - gy0) / RES)); y1 = int(np.ceil((cy + d / 2 - gy0) / RES))
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, W), min(y1, H)
        if mark: occ[y0:y1, x0:x1] = True
    # standoff holes in the corners and fixed pads
    for sx in (BOARD['x0'] + 4, BOARD['x1'] - 4):
        for sy in (BOARD['y0'] + 4, BOARD['y1'] - 4):
            block_area(sx, sy, 8, 8)
    for cx, cy, w, d in FIXED.values(): block_area(cx, cy, w + 1, d + 1)
    block_area(J1_POS[0], J1_POS[1], 16, 11)

    placed = {}
    yy, xx = np.mgrid[0:H, 0:W]
    cxs = gx0 + (xx + 0.5) * RES; cys = gy0 + (yy + 0.5) * RES
    # integral image for fast "fits" tests
    def fits_map(w, d):
        cw, ch = int(np.ceil(w / RES)) + 1, int(np.ceil(d / RES)) + 1
        S = np.pad(occ.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
        ok = np.zeros((H, W), dtype=bool)
        for_y = np.arange(0, H - ch + 1); for_x = np.arange(0, W - cw + 1)
        Y, X = np.meshgrid(for_y, for_x, indexing='ij')
        s = S[Y + ch, X + cw] - S[Y, X + cw] - S[Y + ch, X] + S[Y, X]
        ok[Y, X] = (s == 0)
        # cell (X, Y) is the lower-left corner; convert to centres
        cx = gx0 + (X + cw / 2) * RES; cy = gy0 + (Y + ch / 2) * RES
        return ok, cw, ch

    for it in items:
        ref = it['ref']
        tx, ty = it['target']
        if it.get('near') in placed: tx, ty = placed[it['near']][:2]
        best = None
        for (w, d, rot) in ((it['w'], it['d'], 0), (it['d'], it['w'], 90)) if it.get('rotate') else ((it['w'], it['d'], 0),):
            ok, cw, ch = fits_map(w, d)
            ys, xs = np.nonzero(ok)
            if len(xs) == 0: continue
            cx = gx0 + (xs + cw / 2) * RES; cy = gy0 + (ys + ch / 2) * RES
            dist = np.hypot(cx - tx, cy - ty)
            i = np.argmin(dist)
            if best is None or dist[i] < best[0]:
                best = (dist[i], cx[i], cy[i], w, d, rot)
        if best is None: raise RuntimeError('no room for ' + ref)
        _, cx, cy, w, d, rot = best
        block_area(cx, cy, w + 0.8, d + 0.8)
        placed[ref] = (float(cx), float(cy), rot)
    return placed
