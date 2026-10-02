"""Where everything sits: the perfboard behind the panel, the parts on the panel and the wires.

Units: millimetres in the device frame (x to the right and y up as seen from the FRONT, origin at
the centre of the device). z is measured from the back face of the front panel, negative = deeper.
The board is drawn in the view of the builder: looking at the component side from the rear.
"""
UNIT = 26.0                      # mm per scene unit of the 3D model
PITCH = 2.54
COLS, ROWS = 26, 33              # holes of the 70 x 90 mm board
BOARD = dict(w=70.0, h=90.0, cx=44.0, cy=0.0, thickness=1.6)
STANDOFF = 15.0                  # board front face is 15 mm behind the panel
Z_BOARD_FRONT = -STANDOFF
Z_BOARD_TOP = -STANDOFF - BOARD['thickness']       # component side (rear)

PANEL = {                        # centres of the controls on the front (mm)
    'RV1': (1.5 * UNIT, 0.75 * UNIT),     # Surf
    'RV2': (0.5 * UNIT, -1.1 * UNIT),     # Tide
    'RV3': (1.5 * UNIT, -1.1 * UNIT),     # Tone
    'RV4': (2.5 * UNIT, -1.1 * UNIT),     # Volume
    'SW1': (3.1 * UNIT, 1.55 * UNIT),
    'D2': (2.65 * UNIT, 1.55 * UNIT),
    'SPK1': (-2.15 * UNIT, -0.05 * UNIT),
}
J1_POS = (3.7 * UNIT - 2.6, -0.6 * UNIT, -14.0)     # on the right side wall, inside


def hole(c, r):
    """Hole (column, row) -> device x, y. Looking from the rear: columns grow to the right on screen."""
    x = BOARD['cx'] - (c - (COLS - 1) / 2) * PITCH
    y = BOARD['cy'] + ((ROWS - 1) / 2 - r) * PITCH
    return (round(x, 2), round(y, 2))


# --- sockets and modules (hole coordinates) ----------------------------------------------------------------
PICO_COLS = (3, 10)              # 7 holes = 17.78 mm between the two pin rows of the Pico
PICO_ROW0 = 3                    # pin 1 / pin 40 row
MCP_COLS = (16, 19)              # 7.62 mm between the DIP rows
MCP_ROW0 = 5
AMP_ROW, AMP_COL0 = 25, 3        # the amplifier module's header runs along a row, pins go to the right on screen

def pico_pin(p):
    """Physical pin 1..40 -> hole."""
    if p <= 20: return (PICO_COLS[0], PICO_ROW0 + p - 1)
    return (PICO_COLS[1], PICO_ROW0 + 40 - p)

def mcp_pin(p):
    if p <= 8: return (MCP_COLS[0], MCP_ROW0 + p - 1)
    return (MCP_COLS[1], MCP_ROW0 + 16 - p)

def amp_pin(i):
    """Module header pin 1..7 (VIN, GND, SD, GAIN, DIN, BCLK, LRC)."""
    return (AMP_COL0 + i - 1, AMP_ROW)

# two-pin parts laid out on the board: ref -> (hole of pin 1, hole of pin 2)
TWO_PIN = {
    'D1': {'A': (13, 27), 'K': (17, 27)},
    'C1': {'1': (13, 30), '2': (15, 30)},
    'C2': {'1': (22, 16), '2': (22, 18)},
    'C3': {'1': (22, 20), '2': (22, 22)},
    'C4': {'1': (24, 5), '2': (24, 7)},
    'C5': {'1': (24, 9), '2': (24, 11)},
    'C6': {'1': (24, 13), '2': (24, 15)},
    'C7': {'1': (21, 13), '2': (21, 15)},
    'R1': {'1': (17, 22), '2': (17, 25)},
    'R2': {'1': (20, 29), '2': (20, 32)},
    'Q1': {'C': (21, 24), 'B': (22, 24), 'E': (23, 24)},
}
