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
    thickness=1.57,                              # Adafruit_CAD_Parts "1085 ADS1115 ADC.step" PCB solid, 2026-10-07
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

# --- boards added 2026-10-04 for projects/nutrient_controller, from Adafruit's
# published Eagle files parsed with tools/board_from_eagle.py. Connector facing
# is the tool's inference (pad geometry or nearest edge).
#
# OLED_938: 1.3in 128x64 SSD1306, I2C default (STEMMA QT). The panel
# (package UG-2864HSWEG01_1.3_WRAPAROUND, mirrored) sits on the side opposite
# the components: glass 34.5 x 23.0 centred (0, +0.06), active area
# 29.4 x 14.7 centred (0, +2.11) from the outline centre (tPlace / tDocu layers).
# MOSFET_5648: STEMMA MOSFET driver, AO3406 + 1N4007, 3-30 V load, 1.5 A
# continuous; JST PH3 input, WAGO 2060-402 SMD push-in terminal (X1) out.
# Both holes on one short end: carry the free end.
# RELAY_4409: STEMMA non-latching mini relay; 3.5 mm 3-way terminal block.

OLED_938 = Board(
    name="OLED_938",
    size=(35.560, 33.020),
    holes=((-15.240, -13.970), (15.240, -13.970), (-15.240, 13.970), (15.240, 13.970)),
    hole_dia=2.50,   # Eagle drill; a plated hole finishes smaller than the drill
    source="Adafruit 1.3in 128x64 OLED STEMMA QT.brd, github.com/adafruit/Adafruit-1.3inch-128x64-Mono-OLED-PCB (HEAD), 2026-10-04; Adafruit 1.3in 128x64 OLED STEMMA QT.brd parsed by tools/board_from_eagle.py, 2026-10-04",
    thickness=1.57,   # Adafruit_CAD_Parts "938 Mono 128x64 OLED Stemma.step" PCB solid, 2026-10-07
    nearest_pin=6.35,
    nearest_top_copper=3.79,
    connectors=(
        Connector(-15.24, 0.00, (-1, 0), "JST_SH4"),   # CONN4:JST_SH4, facing by pad geometry
        Connector(15.24, 0.00, (1, 0), "JST_SH4"),   # CONN1:JST_SH4, facing by pad geometry
    ),
)

MOSFET_5648 = Board(
    name="MOSFET_5648",
    size=(25.400, 17.780),
    holes=((10.160, -6.350), (10.160, 6.350)),
    hole_dia=2.50,   # Eagle drill; a plated hole finishes smaller than the drill
    source="Adafruit MOSFET Driver STEMMA Breakout.brd, github.com/adafruit/Adafruit-MOSFET-Driver-STEMMA-PCB (HEAD), 2026-10-04; Adafruit MOSFET Driver STEMMA Breakout.brd parsed by tools/board_from_eagle.py, 2026-10-04",
    thickness=1.57,   # Adafruit_CAD_Parts "5648 MOSFET Driver.step" PCB solid, 2026-10-07
    nearest_pin=6.38,
    nearest_top_copper=1.27,
    connectors=(
        Connector(-8.06, 0.00, (-1, 0), "JST_PH3"),   # X4:JSTPH3, facing by nearest edge
    ),
)

RELAY_4409 = Board(
    name="RELAY_4409",
    size=(34.290, 21.590),
    holes=((-14.605, -8.255), (14.605, -8.255), (-14.605, 8.255), (14.605, 8.255)),
    hole_dia=2.50,   # Eagle drill; a plated hole finishes smaller than the drill
    source="Adafruit Non-Latching Relay Breakout.brd, github.com/adafruit/Adafruit-STEMMA-Non-Latching-Mini-Relay-PCB (HEAD), 2026-10-04; Adafruit Non-Latching Relay Breakout.brd parsed by tools/board_from_eagle.py, 2026-10-04",
    thickness=None,   # not in an Eagle file: caliper
    nearest_pin=5.71,
    nearest_top_copper=1.17,
    connectors=(
        Connector(-12.64, 0.00, (-1, 0), "JST_PH3"),   # X4:JSTPH3, facing by nearest edge
    ),
)

# DFRobot SEN0244 Gravity analog TDS signal board. Outline 42 x 32, four
# holes on 35.00 x 25.00 (both dimensioned) in SEN0244_analog-tds-sensor_
# layout_V1.0.pdf (DFRobot wiki "Layout" download). Hole diameter is drawn,
# not dimensioned: about 3.05 scaled from the vector PDF, so an M2.5 screw.
# XH2.54-2P probe header on one 32 mm edge, PH2.0-3P signal header on the
# other, both side entry and centred (same PDF, scaled). Tallest part is the
# XH header (connectors.JST_XH2, 7.0).
SEN0244 = Board(
    name="SEN0244",
    size=(42.0, 32.0),
    holes=_rect_pattern(35.0, 25.0),
    hole_dia=3.05,                               # scaled from the layout PDF (stroke centreline, 14.705 pt/mm), not dimensioned
    source="SEN0244_analog-tds-sensor_layout_V1.0.pdf, wiki.dfrobot.com SKU SEN0244, read 2026-10-04, re-read 2026-10-07",
    thickness=None,
    # no through-hole pins: the nearest drawn component pad (diode, 4.57 from
    # hole (-17.5, -12.5)) bounds the boss too; the underside is not drawn
    nearest_pin=4.57,
    nearest_top_copper=4.57,                     # same pad; the "A" silkscreen box at 4.11 is not copper
    connectors=(Connector(-21.0 + 6.1 / 2, 0.0, (-1, 0), "JST_XH2"),
                Connector(21.0 - 6.0 / 2, 0.0, (1, 0), "JST_PH3")),
)

# Adafruit Perma-Proto quarter-sized breadboard PCB: a carrier for boards
# without holes (XIAO ESP32-C3, Pololu D24V10F5) and loose parts. From
# `adafruit permaproto quarterbreadboard.brd`, github.com/adafruit/
# Adafruit-Perma-Proto-PCB (HEAD), parsed with tools/board_from_eagle.py on
# 2026-10-04: 1.70 x 2.00 in, two unplated 3.2 holes on the long centreline.
# The breadboard holes are vias (drill 1.2, pad 1.93): the nearest is 3.81
# from each mount hole (Eagle, 2026-10-07), and any of them may carry a
# soldered lead, so it bounds a boss like a pin. Adafruit's STEP
# (Adafruit_CAD_Parts "1608 perma-proto quarter.step") draws the board 1.60
# thick and the holes 3.0; the Eagle drill (3.2) is kept.
PERMAPROTO_QUARTER = Board(
    name="PERMAPROTO_QUARTER",
    size=(43.180, 50.800),
    holes=((-17.780, 0.000), (17.780, 0.000)),
    hole_dia=3.20,
    source="adafruit permaproto quarterbreadboard.brd, github.com/adafruit/Adafruit-Perma-Proto-PCB (HEAD), 2026-10-04",
    thickness=1.60,                              # Adafruit STEP
    nearest_pin=3.81,                            # nearest breadboard via centre, Eagle
    nearest_top_copper=2.85,                     # same via: 3.81 - pad 1.93 / 2
)

# Atlas Scientific Electrically Isolated EZO Carrier Board Gen 2 (one EZO
# circuit; EZOs have no mounting holes of their own). Outline 32 x 42 and hole
# pitch 24 x 34 from the Atlas datasheet electrically-isolated-ezo-carrier-board.pdf
# V1.6 p.2 (files.atlas-scientific.com, read 2026-10-07; Atlas ships #4-40
# screws on 11 mm standoffs). Atlas's own STEP model
# (Electrically-Isolated-EZO-Carrier-Board.zip, same site) gives what the
# drawing does not: holes centred, 4 from every edge (corner r 4 on each
# hole), hole dia 3.0, PCB 1.59. Board frame: +Y = 5-pin header end, -Y = SMA.
# In the STEP, not on the Gen 2 drawing: a 4-pin part on the -X long edge
# (x -15.35..-9.35, y -12.10..-0.60, 10.0 above the top, 2.51 below); kept as an
# envelope. The SMA reaches 9.6 past the -Y edge and 2.0 below the underside.
# Placed on EZO_ISO_x2 without its standoffs, the STEP intersects neither plate,
# screws nor nuts (interference 0.0, 2026-10-07).
EZO_CARRIER_ISO = Board(
    name="EZO_CARRIER_ISO",
    size=(32.0, 42.0),
    holes=_rect_pattern(24.0, 34.0),             # ±12, ±17
    hole_dia=3.0,                                # Atlas STEP; #4-40 (2.84) is the vendor screw: M3 does not pass
    source="Atlas electrically-isolated-ezo-carrier-board.pdf V1.6 p.2 + Atlas STEP model, files.atlas-scientific.com, 2026-10-07",
    thickness=1.59,                              # Atlas STEP
    nearest_pin=6.54,                            # 5-pin header pin (-5.61, 15.63) to hole (-12, 17), Atlas STEP
    nearest_top_copper=4.90,                     # 4-pin part body to hole (-12, -17); nearest SMD pad is 5.76
)

# Atlas Scientific Surveyor analog pH meter, V3.0 ("Gravity analog pH" in
# older Atlas pages). Outline 42 x 32 and hole pitch 34 x 24 from the Atlas
# datasheet Surveyor-pH-datasheet.pdf p.2 (files.atlas-scientific.com, read
# 2026-10-07; Atlas ships 11 mm standoffs). Atlas's STEP (pH-Gravity.zip, same
# site) gives what the drawing does not: holes dia 3.0 (so M2.5; M3 does not
# pass), the hole pattern 0.05 to +X of the outline centre, PCB 1.59. Board
# frame: -X = female SMA (probe), reaching 9.3 past the edge and 1.91 below
# the underside; +X = 3-pin 2.54 right-angle header (-, +, A). Nearest part to
# a hole in plan, by bounding box: 6.40 (top side), so the boss bound uses it
# for both pin and copper. No plug envelope for the SMA or the 2.54 header in
# connectors.py yet: a flat plate puts nothing in front of either short end.
SURVEYOR_PH = Board(
    name="SURVEYOR_PH",
    size=(42.0, 32.0),
    holes=((-16.95, -12.0), (-16.95, 12.0), (17.05, -12.0), (17.05, 12.0)),
    hole_dia=3.0,                                # Atlas STEP
    source="Atlas Surveyor-pH-datasheet.pdf p.2 + Atlas STEP pH-Gravity.zip, files.atlas-scientific.com, 2026-10-07",
    thickness=1.59,                              # Atlas STEP
    nearest_pin=6.40,                            # nearest part bbox to a hole, Atlas STEP (no through-hole pin is closer)
    nearest_top_copper=6.40,
)

BOARDS = {b.name: b for b in (ADS1115, ADS1115_V1, UNO_R3, TENTACLE_T2, INA219, TCA9548A, BME280, FEATHER_ESP32S3, OLED_938,
                                     MOSFET_5648, RELAY_4409, SEN0244, PERMAPROTO_QUARTER, EZO_CARRIER_ISO, SURVEYOR_PH)}
