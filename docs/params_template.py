"""params_template.py — skeleton of the convention in PARAMS_CONVENTION.md.

Copy into projects/<name>/params.py, rename the SIZES keys to your family axis, fill COMMON, write derive()
and validate(). Keep the three invariants:
    - nothing downstream of this file holds a number
    - validate() raises on anything not physically obtainable
    - inactive sizes still validate, only ACTIVE_SIZES build
projects/standoff_plate/params.py is the worked example.
"""
from __future__ import annotations

import math
from types import MappingProxyType

from cacad.registries.materials import CLEAR_LOOSE, LAYER, NOZZLE, WALL

COMMON = MappingProxyType(
    dict(
        # --- named clearances (mm): say which two surfaces each one separates ---
        screw_clearance=CLEAR_LOOSE,   # diametral: bore - screw nominal (materials TODO until the coupon)
        slide_clearance=0.2,           # diametral: bore - the part that slides in it
        # --- geometry rules ---
        wall=WALL,                     # 4 perimeters
        margin=3.0,                    # plate edge beyond the thing it carries
        # --- manufacturing rules ---
        nozzle_d=NOZZLE,
        layer=LAYER,
        min_wall=1.2,                  # functional floor; 2 * nozzle_d is the printable floor
        max_overhang_deg=60.0,
        material="PETG",
        bbox_tol=0.05,
    )
)

PRINT_ORIENTATION = MappingProxyType(dict(
    # bed_z is a number or the name of a derived key; overhang_exceptions name a ceiling and its z
    body=dict(up=(0, 0, 1), bed_face="bottom face", bed_z="0", known_overhangs=[], overhang_exceptions=[]),
))

SIZES = {
    # Inputs only. Mark starting values UNVERIFIED; that never excuses a validate() failure.
    "S1": dict(  # UNVERIFIED
        screw_d=3.0, length_a=10.0,
        purchased_part="ISO 4032 M3", purchased_part_h=2.4,   # a bought dimension names its standard
    ),
}

ACTIVE_SIZES = ("S1",)


def derive(size: str, **overrides) -> dict:
    """Every dimension the build scripts need. Overrides are for what-if tables only."""
    s = dict(SIZES[size])
    c = dict(COMMON)
    for k, v in overrides.items():
        (s if k in s else c)[k] = v
    d = dict(size=size, **s, **c)

    d["bore_d"] = s["screw_d"] + c["screw_clearance"]
    d["boss_d"] = d["bore_d"] + 2 * c["wall"]
    # a shared dimension is the max() of the requirements that compete for it, and the winner is recorded
    needs = {"requirement A": 0.3 / math.tan(math.radians(15)), "requirement B": 0.12 * s["length_a"]}
    d["height_governed_by"], d["height"] = max(needs.items(), key=lambda kv: kv[1])
    # a depth that a purchased part consumes is derived from that part, not typed in
    d["pocket_depth"] = math.ceil((s["purchased_part_h"] + 0.4) / c["layer"]) * c["layer"]

    d["print_orientation"] = {k: dict(v, bed_z=float(v["bed_z"]) if v["bed_z"].replace(".", "").isdigit() else d[v["bed_z"]])
                              for k, v in PRINT_ORIENTATION.items()}
    d["walls"] = {"boss wall": c["wall"]}
    return d


def validate(size: str) -> dict:
    """Raise AssertionError on anything not buildable or not usable. No warnings."""
    d = derive(size)
    for name, w in d["walls"].items():
        assert w >= d["min_wall"], f"{size}: wall {name} = {w:.2f} < {d['min_wall']}"
        assert w >= 2 * d["nozzle_d"], f"{size}: wall {name} = {w:.2f} < 2 x nozzle"
    assert d["purchased_part"].split()[0] in ("ISO", "DIN"), f"{size}: purchased part must name a standard"
    assert d["pocket_depth"] >= d["purchased_part_h"], f"{size}: pocket shallower than the purchased part"
    return d


if __name__ == "__main__":
    for size in SIZES:
        try:
            d = validate(size)
            print(f"{size}: ok  height {d['height']:.2f} ({d['height_governed_by']}), pocket {d['pocket_depth']}")
        except AssertionError as e:
            print(f"{size}: FAIL: {e}")
