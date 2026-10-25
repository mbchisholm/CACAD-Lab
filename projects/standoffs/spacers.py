"""M3 PCB standoff spacers — round, unthreaded, printed standing (axis = Z).

Bore = M3 nominal + CLEAR_LOOSE (calibrated after the coupon; 0.40 until then).
Lengths are a ladder; once one is chosen it belongs in a params.py.
"""
from build123d import *
from cacad.registries.materials import CLEAR_LOOSE

SCREW_NOMINAL = 3.0
BORE = SCREW_NOMINAL + CLEAR_LOOSE      # 3.40
OD = 6.0
LENGTHS = [5, 8, 10, 12, 15]
CHAMFER = 0.4                            # outer edges only; eases elephant's foot
GAP = 4.0                                # spacing between spacers in the combined STL


def spacer(length):
    with BuildPart() as sp:
        Cylinder(OD / 2, length, align=(Align.CENTER, Align.CENTER, Align.MIN))
        chamfer(sp.edges().filter_by(GeomType.CIRCLE).filter_by(lambda e: e.radius > OD / 2 - 0.01), CHAMFER)
        with Locations((0, 0, length)):
            Hole(BORE / 2)
    return sp.part


singles = [spacer(L) for L in LENGTHS]
result = Compound([p.moved(Location((i * (OD + GAP), 0, 0))) for i, p in enumerate(singles)])

if __name__ == "__main__":
    from cacad import export
    OUT = __file__.rsplit("/", 1)[0] + "/out"   # a string: the MCP sandbox rejects pathlib/os anywhere in this file
    for L, p in zip(LENGTHS, singles):
        bb = p.bounding_box()
        print(f"L={L:>2}: bbox {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f}, "
              f"volume {p.volume:.1f} mm^3, solids {len(p.solids())}, valid {p.is_valid}")
        export(p, f"spacer_M3_L{L}", OUT)
    export(result, "spacers_M3_ladder", OUT)
    bb = result.bounding_box()
    print(f"ladder: bbox {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f}, solids {len(result.solids())}")
