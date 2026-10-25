"""Open-top tray enclosure with bossed mounting holes for boards from boards.py
and a rim slot for a cable.

    tray([(ADS1115, (-15.7, 0)), (ADS1115, (15.7, 0))], screw="M2")
"""
from build123d import *
from cacad.registries.materials import CLEAR_LOOSE, WALL, BOSS_OD_M3
from cacad.registries.boards import ADS1115

SCREW = {"M2": 2.0, "M2.5": 2.5, "M3": 3.0}

FLOOR_T = 2.0        # tray floor
WALL_H = 25.0        # wall height above the floor top: boss 8 + board + header + plug
MARGIN = 5.0         # clear space between any board edge and the inner wall
STANDOFF = 8.0       # boss height above floor
CORNER_R = 3.0       # outer vertical corner radius
SLOT_W = 8.0         # cable slot width, from the rim down
SLOT_DEPTH = 12.0    # slot depth from the rim; bottom sits above board level


def tray(placements, screw="M2", cable_side="+X"):
    bore = SCREW[screw] + CLEAR_LOOSE
    boss_od = BOSS_OD_M3 if screw == "M3" else bore + 2 * 1.5

    xs = [p[0] + s * b.size[0] / 2 for b, p in placements for s in (-1, 1)]
    ys = [p[1] + s * b.size[1] / 2 for b, p in placements for s in (-1, 1)]
    ix0, ix1 = min(xs) - MARGIN, max(xs) + MARGIN
    iy0, iy1 = min(ys) - MARGIN, max(ys) + MARGIN
    inner = (ix1 - ix0, iy1 - iy0)
    cx, cy = (ix0 + ix1) / 2, (iy0 + iy1) / 2
    outer = (inner[0] + 2 * WALL, inner[1] + 2 * WALL)
    height = FLOOR_T + WALL_H

    with BuildPart() as tr:
        with Locations((cx, cy, height / 2)):
            Box(*outer, height)
        fillet(tr.edges().filter_by(Axis.Z), radius=CORNER_R)

        # cavity: everything above the floor, inside the walls
        with Locations((cx, cy, FLOOR_T + WALL_H / 2)):
            Box(*inner, WALL_H, mode=Mode.SUBTRACT)
        fillet(tr.edges().filter_by(Axis.Z).filter_by(lambda e: abs(e.center().X - cx) < inner[0] / 2 + 0.01),
               radius=CORNER_R - WALL)

        # bosses + through holes
        hole_pts = [(bx + hx, by + hy) for b, (bx, by) in placements for hx, hy in b.holes]
        with Locations(*[(x, y, FLOOR_T) for x, y in hole_pts]):
            Cylinder(boss_od / 2, STANDOFF, align=(Align.CENTER, Align.CENTER, Align.MIN))
        with Locations(*[(x, y, FLOOR_T + STANDOFF) for x, y in hole_pts]):
            Hole(bore / 2)

        # cable slot: U-shape cut down from the rim through one end wall
        sx = ix1 + WALL / 2 if cable_side == "+X" else ix0 - WALL / 2
        with BuildSketch(Plane.YZ.offset(sx)) as sk:
            with Locations((cy, height - SLOT_DEPTH / 2)):
                SlotOverall(SLOT_DEPTH + SLOT_W, SLOT_W, rotation=90)
        extrude(sk.sketch, amount=WALL, both=True, mode=Mode.SUBTRACT)

    return tr.part, {"inner": inner, "outer": outer, "height": height, "holes": hole_pts, "bore": bore}


# default configuration: two ADS1115 side by side, 6 mm apart, M2
GAP = 6.0
DX = ADS1115.size[0] / 2 + GAP / 2          # 15.7
PLACEMENTS = [(ADS1115, (-DX, 0)), (ADS1115, (DX, 0))]
result, info = tray(PLACEMENTS, screw="M2")

if __name__ == "__main__":
    from cacad import export
    OUT = __file__.rsplit("/", 1)[0] + "/out"   # a string: the MCP sandbox rejects pathlib/os anywhere in this file
    part = result
    bb = part.bounding_box()
    print(f"outer {info['outer'][0]:.2f} x {info['outer'][1]:.2f} x {info['height']:.1f}  "
          f"inner {info['inner'][0]:.2f} x {info['inner'][1]:.2f}")
    print(f"bbox {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f}, volume {part.volume:.0f}, "
          f"solids {len(part.solids())}, valid {part.is_valid}")
    print("holes:", [(round(x, 2), round(y, 2)) for x, y in info["holes"]], "bore", info["bore"])
    export(part, "tray_2xADS1115_M2", OUT)
