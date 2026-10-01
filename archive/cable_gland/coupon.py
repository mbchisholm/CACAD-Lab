"""Print coupon = CLEARANCE LADDER.

One plate, declared print orientations, exported as individual STLs, a plate
STL and a plate 3MF (one named object per part):

    coupon_body           the production body: 13 mm panel thread, gasket recess
                          + foot, hex with stop ring, neck thread, seat
    coupon_nut_c0.150 ..  five production nuts built at thread_clearance =
    coupon_nut_c0.450     0.15 / 0.225 / 0.30 / 0.375 / 0.45 mm (diametral),
                          each embossed with its clearance on the +Y flat
    coupon_collet         the production collet

Every nut is checked with its own clearance; only the label is extra. Write
the printed result into harvest/FINDINGS.md -> TODO -> clearance ladder.

    python coupon.py [M16]
"""
from __future__ import annotations

import sys

from build123d import Compound, Location

import params
from body import build_body, check_body
from collet import build_collet, check_collet
from cacad import export_3mf
from cacad.checks.orientation import to_print_orientation
from common import OUT_DIR, export
from nut import build_nut, check_nut

LADDER = (0.15, 0.225, 0.30, 0.375, 0.45)   # thread_clearance, diametral mm
NUT_PITCH_X = 32.0                           # plate spacing; nut across-corners is 27.7
ROW_Y = 36.0


def build_ladder(size: str) -> dict:
    d = params.derive(size)
    placed: dict[str, object] = {}

    body = build_body(size)
    check_body(body, size)
    placed["coupon_body"] = to_print_orientation(body, d["print_orientation"]["body"])

    for i, clr in enumerate(LADDER):
        nut = build_nut(size, **{"thread_clearance": clr})
        check_nut(nut, size, thread_clearance=clr)
        labelled = build_nut(size, label=f"{clr:.3f}", thread_clearance=clr)
        assert labelled.is_valid and len(labelled.solids()) == len(nut.solids())
        x = (i - (len(LADDER) - 1) / 2) * NUT_PITCH_X
        placed[f"coupon_nut_c{clr:.3f}"] = to_print_orientation(labelled, d["print_orientation"]["nut"]).moved(Location((x, ROW_Y, 0)))

    collet = build_collet(size)
    check_collet(collet, size)
    placed["coupon_collet"] = to_print_orientation(collet, d["print_orientation"]["collet"]).moved(Location((30, 0, 0)))

    for name, part in placed.items():
        bb = part.bounding_box()
        assert abs(bb.min.Z) < d["bbox_tol"], f"{name}: bed face is not on z=0"
        export(part, f"{name}_{size}")

    plate = Compound(children=list(placed.values()), label=f"coupon_plate_{size}")
    export(plate, f"coupon_plate_{size}")
    export_3mf(placed, OUT_DIR / f"coupon_plate_{size}.3mf")   # one mesh per part, not per solid

    bb = plate.bounding_box()
    print(f"plate {bb.size.X:.0f} x {bb.size.Y:.0f} x {bb.size.Z:.1f} mm: body neck-down, {len(LADDER)} nuts open-face-down "
          f"(clearances {', '.join(f'{c:.3f}' for c in LADDER)}), collet base-down")
    print(f"panel thread {d['panel_thread_len']} mm for {d['locknut']}; nut engagement {d['nut_thread_len']} mm; "
          f"production thread_clearance {d['thread_clearance']}")
    print("known overhangs:", d["print_orientation"]["body"]["known_overhangs"] + d["print_orientation"]["nut"]["known_overhangs"])
    print(f"-> {OUT_DIR}/coupon_*_{size}.stl, coupon_plate_{size}.stl, coupon_plate_{size}.3mf")
    return placed


if __name__ == "__main__":
    size = next((a for a in sys.argv[1:] if a in params.SIZES), params.ACTIVE_SIZES[0])
    build_ladder(size)
