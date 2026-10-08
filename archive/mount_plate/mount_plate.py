"""Mounting plate generator: a flat plate with pre-drilled holes for one or
more boards from the board registry (cacad.registries.boards).

    plate = mount_plate([(ADS1115, (0, 0))])            # flat, use loose spacers
    plate = mount_plate([(ADS1115, (0, 0))], standoff=8) # integrated bosses

Holes are screw clearance (nominal + CLEAR_LOOSE). Board outlines are engraved
on the top face as a placement guide and each board is labeled.
"""
from build123d import *
from cacad.registries.materials import CLEAR_LOOSE, LAYER, BOSS_OD_M3
from cacad.registries.boards import BOARDS

SCREW = {"M2": 2.0, "M2.5": 2.5, "M3": 3.0}

PLATE_T = 3.0            # plate thickness (design choice; nut + screw head land on it)
MARGIN = 4.0             # plate extends this far past every board outline
ENGRAVE = 2 * LAYER      # 0.4 mm outline groove
EMBOSS = 3 * LAYER       # 0.6 mm label
OUTLINE_W = 0.8          # groove width, 2 extrusion widths


def mount_plate(placements, screw="M3", standoff=0.0, margin=MARGIN, thickness=PLATE_T):
    """placements: [(Board, (x, y)), ...] board centers on the plate, mm.
    standoff: 0 = flat plate (use loose spacers); >0 = printed bosses of that height."""
    bore = SCREW[screw] + CLEAR_LOOSE
    boss_od = BOSS_OD_M3 if screw == "M3" else bore + 2 * 1.5   # 1.5 mm wall each side

    xs = [p[0] + s * b.size[0] / 2 for b, p in placements for s in (-1, 1)]
    ys = [p[1] + s * b.size[1] / 2 for b, p in placements for s in (-1, 1)]
    x0, x1 = min(xs) - margin, max(xs) + margin
    y0, y1 = min(ys) - margin, max(ys) + margin

    with BuildPart() as mp:
        with Locations(((x0 + x1) / 2, (y0 + y1) / 2, thickness / 2)):
            Box(x1 - x0, y1 - y0, thickness)

        for board, (bx, by) in placements:
            hole_pts = [(bx + hx, by + hy) for hx, hy in board.holes]

            # outline groove on the plate top
            with BuildSketch(Plane.XY.offset(thickness)) as sk:
                with Locations((bx, by)):
                    Rectangle(board.size[0] + OUTLINE_W, board.size[1] + OUTLINE_W)
                    Rectangle(board.size[0] - OUTLINE_W, board.size[1] - OUTLINE_W, mode=Mode.SUBTRACT)
            extrude(sk.sketch, amount=-ENGRAVE, mode=Mode.SUBTRACT)

            with BuildSketch(Plane.XY.offset(thickness)) as sk:
                with Locations((bx, by)):
                    Text(board.name, font_size=4, font_style=FontStyle.BOLD)
            extrude(sk.sketch, amount=EMBOSS)

            if standoff > 0:  # start below the groove floor so no void is left under the boss
                with Locations(*[(x, y, thickness - ENGRAVE) for x, y in hole_pts]):
                    Cylinder(boss_od / 2, standoff + ENGRAVE, align=(Align.CENTER, Align.CENTER, Align.MIN))

            with Locations(*[(x, y, thickness + standoff) for x, y in hole_pts]):
                Hole(bore / 2)

    return mp.part


# default configuration: one ADS1115, M2 (holes ~2.5 mm; M2 screws on hand, 2026-09-14)
SCREW_DEFAULT = "M2"
VARIANTS = {"flat": dict(standoff=0.0), "boss8": dict(standoff=8.0)}
result = mount_plate([(BOARDS["ADS1115"], (0, 0))], screw=SCREW_DEFAULT, **VARIANTS["boss8"])

if __name__ == "__main__":
    from cacad import export
    OUT = __file__.rsplit("/", 1)[0] + "/out"   # a string: the MCP sandbox rejects pathlib/os anywhere in this file
    screw = SCREW_DEFAULT
    for tag, kw in VARIANTS.items():
        part = mount_plate([(BOARDS["ADS1115"], (0, 0))], screw=screw, **kw)
        bb = part.bounding_box()
        print(f"{tag}: bbox {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f}, "
              f"volume {part.volume:.1f}, solids {len(part.solids())}, valid {part.is_valid}")
        export(part, f"mount_ADS1115_{screw}_{tag}", OUT)
