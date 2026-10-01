"""Calibration coupon — A1 / PETG.

Clearance ladder: 5 mm nominal through-holes at +0.10..+0.30.
Insert bore ladder: M3 heat-set bores 3.8..4.2 mm, 6 mm deep, on a raised pad.
20 mm cube at the +X end, bottom flush with the plate, for shrinkage check.
All sizes embossed on the top face.
"""
from build123d import *
from cacad.registries.materials import LAYER, INSERT_DEPTH_M3

# --- plate -------------------------------------------------------------
PLATE_X, PLATE_Y, PLATE_T = 120.0, 50.0, 4.0
CUBE = 20.0

# --- ladders -----------------------------------------------------------
CLEAR_NOMINAL = 5.0
CLEAR_OFFSETS = [0.10, 0.15, 0.20, 0.25, 0.30]
CLEAR_DIAS = [round(CLEAR_NOMINAL + o, 2) for o in CLEAR_OFFSETS]
BORE_DIAS = [3.8, 3.9, 4.0, 4.1, 4.2]
BORE_DEPTH = INSERT_DEPTH_M3          # 6.0
PITCH = 18.0
COL_X = [-42 + PITCH * i for i in range(5)]   # -42 .. 30; cube starts at 40
HEADER_X = -54.0

CLEAR_Y, CLEAR_LABEL_Y = 10.0, 20.0
PAD_Y0, PAD_Y1, PAD_H = -25.0, -7.0, 4.0     # pad on top of plate -> 8 mm total
BORE_Y, BORE_LABEL_Y = -12.0, -20.0
PAD_TOP = PLATE_T + PAD_H                     # 8.0

# --- text --------------------------------------------------------------
FONT_SIZE = 5.0
EMBOSS = 3 * LAYER                            # 0.6 mm raised


def label(txt, x, y, z, size=FONT_SIZE):
    with BuildSketch(Plane.XY.offset(z)) as sk:
        with Locations((x, y)):
            Text(txt, font_size=size, font_style=FontStyle.BOLD)
    extrude(sk.sketch, amount=EMBOSS)


with BuildPart() as coupon:
    # plate, bottom at z=0
    with Locations((0, 0, PLATE_T / 2)):
        Box(PLATE_X, PLATE_Y, PLATE_T)

    # raised pad for the insert bores (z 4..8)
    pad_x0, pad_x1 = -PLATE_X / 2 + 1, PLATE_X / 2 - CUBE - 1   # -59 .. 39
    with Locations(((pad_x0 + pad_x1) / 2, (PAD_Y0 + PAD_Y1) / 2, PLATE_T + PAD_H / 2)):
        Box(pad_x1 - pad_x0, PAD_Y1 - PAD_Y0, PAD_H)

    # 20 mm cube at +X end, bottom flush with plate bottom
    with Locations((PLATE_X / 2 - CUBE / 2, 0, CUBE / 2)):
        Box(CUBE, CUBE, CUBE)

    # clearance ladder: through holes, cut from plate top
    for x, d in zip(COL_X, CLEAR_DIAS):
        with Locations((x, CLEAR_Y, PLATE_T)):
            Hole(radius=d / 2)

    # insert bore ladder: blind, cut from pad top
    for x, d in zip(COL_X, BORE_DIAS):
        with Locations((x, BORE_Y, PAD_TOP)):
            Hole(radius=d / 2, depth=BORE_DEPTH)

    # labels
    for x, d in zip(COL_X, CLEAR_DIAS):
        label(f"{d:.2f}", x, CLEAR_LABEL_Y, PLATE_T)
    for x, d in zip(COL_X, BORE_DIAS):
        label(f"{d:.1f}", x, BORE_LABEL_Y, PAD_TOP)
    label("CLR", HEADER_X, CLEAR_Y, PLATE_T, size=4)
    label("M3", HEADER_X, BORE_Y, PAD_TOP, size=4)
    label("PETG A1 2026-09-14", -6, 0, PLATE_T, size=4)

part = coupon.part
result = part

if __name__ == "__main__":
    from cacad import export
    OUT = __file__.rsplit("/", 1)[0] + "/out"   # a string: the MCP sandbox rejects pathlib/os anywhere in this file
    bb = part.bounding_box()
    print("bbox size:", bb.size)
    print("bbox min:", bb.min, " max:", bb.max)
    print("volume mm^3:", round(part.volume, 1))
    print("valid:", part.is_valid, " solids:", len(part.solids()))
    print("exported", *export(part, "fdm_coupon", OUT))
