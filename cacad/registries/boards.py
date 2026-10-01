"""Board registry: outline and mounting-hole numbers for boards in a design.

Every value comes from a datasheet drawing or a caliper. Cite the source.
UNO_R3 and TENTACLE_T2 were measured for a stacking experiment (2026-09-16)
and are kept for the numbers.
Coordinates are mm, relative to the board's outline center, +Y = "top" of
the drawing.
"""
from dataclasses import dataclass, field

IN = 25.4


@dataclass(frozen=True)
class Connector:
    """A board-edge connector: its origin on the board, the outward direction
    its mouth faces (unit vector, board frame) and the mating system in
    cacad.registries.connectors."""
    x: float
    y: float
    facing: tuple
    kind: str


@dataclass(frozen=True)
class Board:
    name: str
    size: tuple            # (X, Y) outline, mm
    holes: tuple           # ((x, y), ...) relative to outline center, mm
    hole_dia: float | None # board's own hole diameter, mm; None = not yet measured
    source: str = ""
    thickness: float | None = None  # PCB thickness, mm; None = not yet known
    # Radii around a mounting hole that a mount may occupy, minimum over the
    # holes (tools/board_from_eagle.py prints them per hole). None = unknown.
    nearest_pin: float | None = None        # hole centre -> nearest through-hole pin centre; bounds a boss under the board
    nearest_top_copper: float | None = None  # hole centre -> nearest component copper edge on top; bounds a screw head
    connectors: tuple = ()                   # (Connector, ...); an enclosure sizes openings and plug room from these


def _rect_pattern(px, py):
    """Four holes on a rectangle of pitch px × py, centered."""
    return tuple((sx * px / 2, sy * py / 2) for sx in (-1, 1) for sy in (-1, 1))


# Adafruit ADS1115 breakout (PID 1085), current STEMMA QT revision. From the
# Eagle board file `Adafruit ADS1115 ADC STEMMA QT.brd` in
# github.com/adafruit/ADS1X15-Breakout-Board-PCBs (master), parsed with
# tools/board_from_eagle.py on 2026-09-20: outline 1.00 × 0.70 in, four
# MOUNTINGHOLE_2.5_PLATED at 0.10 in from the edges, header pin row 0.15 in
# from the hole row. Drill 2.5 plated finishes under 2.5: M2 screws, not M2.5.
ADS1115 = Board(
    name="ADS1115",
    size=(1.00 * IN, 0.70 * IN),                 # 25.40 × 17.78
    holes=_rect_pattern(0.80 * IN, 0.50 * IN),   # ±10.16, ±6.35
    hole_dia=2.5,                                # Eagle drill, plated
    source="Adafruit ADS1115 ADC STEMMA QT.brd, github.com/adafruit/ADS1X15-Breakout-Board-PCBs, 2026-09-20",
    thickness=None,                              # not in the Eagle file: caliper
    nearest_pin=3.81,                            # header row at ±2.54 vs holes at ±6.35
    nearest_top_copper=2.11,                     # hole (-10.16, +6.35)
    # JST_SH4 packages CONN3 (rot R90) and CONN4 (rot R270) at x = ±10.03 on the short ends, mouths outward
    connectors=(Connector(10.03, 0.0, (1, 0), "JST_SH4"), Connector(-10.03, 0.0, (-1, 0), "JST_SH4")),
)

# The original two-hole revision of the same product, same repository
# (`Adafruit_ADS1115_16Bit_I2C_ADC.brd`): 1.10 × 0.675 in, both holes on one
# long edge. A plate for it must carry the free edge (see projects/standoff_plate).
ADS1115_V1 = Board(
    name="ADS1115_V1",
    size=(27.94, 17.145),
    holes=((-11.43, 6.032), (11.43, 6.032)),
    hole_dia=2.5,
    source="Adafruit_ADS1115_16Bit_I2C_ADC.brd, github.com/adafruit/ADS1X15-Breakout-Board-PCBs, 2026-09-20",
    thickness=None,
    nearest_pin=12.70,
    nearest_top_copper=2.39,
)

# Arduino Uno R3. Outline 68.58 x 53.34 (2.70 x 2.10 in). Hole coordinates are
# board-local with the origin at the bottom-left corner and USB at top-left,
# then re-based to the outline center. Two independent sources agree on the
# pattern to 0.01 mm: KiCad 10.0.4 Module.pretty/Arduino_UNO_R3_WithMountingHoles
# (drill 3.2) and the Tentacle T2 Edge.Cuts/NPTH loaded via KiCadStepUp.
# Component heights are not here; nothing official publishes them.
_UNO_SIZE = (68.58, 53.34)
_UNO_HOLES_LOCAL = ((13.97, 2.58), (15.24, 50.84), (66.04, 7.66), (66.04, 35.60))
_UNO_HOLES = tuple((x - _UNO_SIZE[0] / 2, y - _UNO_SIZE[1] / 2) for x, y in _UNO_HOLES_LOCAL)

UNO_R3 = Board(
    name="UNO_R3",
    size=_UNO_SIZE,
    holes=_UNO_HOLES,        # (-20.32,-24.09) (-19.05,24.17) (31.75,-19.01) (31.75,8.93)
    hole_dia=3.2,
    source="KiCad 10.0.4 Arduino_UNO_R3_WithMountingHoles footprint + Tentacle T2 kicad_pcb, 2026-09-16",
)

# Whitebox Tentacle T2 mini, an Uno-format shield: same outline and holes.
# Stacking headers reach 8.86 mm below the underside and 8.50 above the top
# (from the shield's own 3D models via StepUp, 2026-09-16).
TENTACLE_T2 = Board(
    name="TENTACLE_T2",
    size=_UNO_SIZE,
    holes=_UNO_HOLES,
    hole_dia=3.2,
    source="tentacle-mini.kicad_pcb (KiCad 5.1) via KiCadStepUp 11.09.6, 2026-09-16",
    thickness=1.6,
)

# --- boards added 2026-09-21, all from Adafruit's published Eagle files parsed
# with tools/board_from_eagle.py (holes, drill, keepouts, connector positions;
# connector facing from the JST pad geometry or the nearest edge, as noted).

# Adafruit INA219 STEMMA QT (current/power monitor). Four holes on 0.80 x 0.60 in;
# JST SH4 on both short ends, like the ADS1115.
INA219 = Board(
    name="INA219",
    size=(25.40, 20.32),
    holes=((-10.16, -7.62), (10.16, -7.62), (-10.16, 7.62), (10.16, 7.62)),
    hole_dia=2.5,
    source="Adafruit INA219 STEMMA QT.brd, github.com/adafruit/Adafruit-INA219-Current-Sensor-PCB, 2026-09-21",
    thickness=None,
    nearest_pin=3.81,
    nearest_top_copper=2.42,
    connectors=(Connector(10.16, 0.0, (1, 0), "JST_SH4"), Connector(-10.16, 0.0, (-1, 0), "JST_SH4")),
)

# Adafruit TCA9548A I2C multiplexer (this revision: headers only, no STEMMA QT).
# Two holes on the long centreline, 25.4 apart; header rows on the long edges.
TCA9548A = Board(
    name="TCA9548A",
    size=(17.78, 30.48),
    holes=((0.0, -12.7), (0.0, 12.7)),
    hole_dia=2.5,
    source="Adafruit TCA9548A.brd, github.com/adafruit/Adafruit-TCA9548A-I2C-Multiplexer-PCB, 2026-09-21",
    thickness=None,
    nearest_pin=7.73,
    nearest_top_copper=2.59,
)

# Adafruit BME280 breakout (this revision: headers only). Two holes on one
# long edge, 12.7 apart: cantilevers like ADS1115_V1.
BME280 = Board(
    name="BME280",
    size=(17.78, 19.05),
    holes=((-6.35, 6.985), (6.35, 6.985)),
    hole_dia=2.2,
    source="Adafruit BME280.brd, github.com/adafruit/Adafruit-BME280-Breakout-PCB, 2026-09-21",
    thickness=None,
    nearest_pin=14.03,
    nearest_top_copper=2.26,
)

# Adafruit Feather ESP32-S3 (8 MB, no PSRAM). Feather outline 2.00 x 0.90 in;
# the two USB-end holes are plain 2.2 drills, the other two 2.5 plated, so
# hole_dia is 2.2 and M2 is the screw. USB-C at the -X end (nearest edge);
# STEMMA QT mid-board, mouth towards the USB end (JST pad geometry); JST PH
# battery connector on the +Y edge (nearest edge).
FEATHER_ESP32S3 = Board(
    name="FEATHER_ESP32S3",
    size=(50.80, 22.86),
    holes=((22.86, -9.588), (-22.86, -8.89), (-22.86, 8.89), (22.86, 9.525)),
    hole_dia=2.2,
    source="Adafruit ESP32-S3 8MB No PSRAM.brd, github.com/adafruit/Adafruit-Feather-ESP32-S3-PCB, 2026-09-21",
    thickness=None,
    nearest_pin=3.85,
    nearest_top_copper=2.25,
    connectors=(Connector(-22.73, 0.0, (-1, 0), "USB_C"),
                Connector(-3.05, 0.0, (-1, 0), "JST_SH4"),
                Connector(-14.48, 7.94, (0, 1), "JST_PH2")),
)

BOARDS = {b.name: b for b in (ADS1115, ADS1115_V1, UNO_R3, TENTACLE_T2, INA219, TCA9548A, BME280, FEATHER_ESP32S3)}
