"""module_grid edge clamp: a grid tile with a fixed grooved jaw and a track, and
a separate sliding jaw that rides on the track on two M3 screws in heat-set
inserts. A board with no published hole pattern (DS18B20 screw-terminal
adapters) is gripped by two opposite edges: each groove has a flat floor and
a 45 deg roof, so closing the jaw pushes the board's top corners down onto
the floors. Both parts print flat on their plates; the roofs are the only
downward faces and they are 45 deg. Every number is from params.derive_clamp.

    .venv/bin/python projects/module_grid/clamp.py     # ACTIVE_CLAMPS -> out/
"""
from __future__ import annotations

from build123d import (Axis, Box, BuildPart, BuildSketch, Compound, Cylinder, Hole, Location, Locations, Mode, Part,
                       Plane, Polygon, Rectangle, SlotCenterToCenter, extrude, fillet)

from cacad import ALIGN_MIN_Z, assert_bbox, assert_material, interference_volume, is_inside, single_solid
from projects.module_grid.params import ACTIVE_CLAMPS, INSERT, M3, derive_clamp, engage, jaw_face


def _groove(d: dict, x_face: float, z_floor: float, sense: float):
    """The groove cut, a prism along Y: floor at z_floor, back wall `groove_back`
    tall at groove_depth into the jaw, a 45 deg roof back out to the face.
    sense = -1 cuts into a jaw that lies at x < x_face, +1 into one at x > x_face."""
    g, b = d["groove_depth"], d["groove_back"]
    out = x_face - sense * 0.5   # the cut starts in the air in front of the face, so it shares no face with the jaw
    pts = [(out, z_floor), (x_face + sense * g, z_floor), (x_face + sense * g, z_floor + b), (x_face, z_floor + b + g),
           (out, z_floor + b + g)]
    with BuildSketch(Plane.XZ) as sk:
        Polygon(*pts, align=None)
    return extrude(sk.sketch, amount=d["jaw_len"] / 2 + 1.0, both=True)


def build_tile(name: str) -> Part:
    d = derive_clamp(name)
    (x0, x1), (y0, y1) = d["tile_x"], d["tile_y"]
    L = d["jaw_len"]
    with BuildPart() as bp:
        with Locations(((x0 + x1) / 2, (y0 + y1) / 2, 0)):
            Box(x1 - x0, y1 - y0, d["plate_t"], align=ALIGN_MIN_Z)
        fillet(bp.edges().filter_by(Axis.Z), radius=d["corner_r"])
        with Locations((-d["jaw_w"] / 2, 0, d["plate_t"])):                    # fixed jaw
            Box(d["jaw_w"], L, d["jaw_top_z"] - d["plate_t"], align=ALIGN_MIN_Z)
        tx0, tx1 = d["track_x"]
        with Locations(((tx0 + tx1) / 2, 0, d["plate_t"])):                    # track for the sliding jaw
            Box(tx1 - tx0, L, d["track_top_z"] - d["plate_t"], align=ALIGN_MIN_Z)
        with Locations(*[(x, y, d["track_top_z"]) for x, y in d["inserts"]]):
            Hole(INSERT["bore"] / 2, d["insert_bore_depth"])
        with Locations(*[(x, y, d["plate_t"]) for x, y in d["mount_holes"]]):
            Hole(d["screw_bore"] / 2, d["plate_t"])
        tx, ty, _ = d["tie"]
        with BuildSketch(Plane.XY) as sk:
            with Locations(*d["ties"]):
                Rectangle(tx, ty)
        extrude(sk.sketch, amount=d["plate_t"], mode=Mode.SUBTRACT)
    return bp.part - _groove(d, 0.0, d["z_l"], -1.0)


def build_jaw(name: str) -> Part:
    """In its own frame: face at x = 0 looking -X, foot running +X, foot bottom at z = 0."""
    d = derive_clamp(name)
    L, h = d["jaw_len"], d["jaw_top_z"] - d["track_top_z"]
    with BuildPart() as bp:
        with Locations((d["foot_len"] / 2, 0, 0)):
            Box(d["foot_len"], L, d["foot_t"], align=ALIGN_MIN_Z)
        with Locations((d["jaw_w"] / 2, 0, 0)):
            Box(d["jaw_w"], L, h, align=ALIGN_MIN_Z)
        with BuildSketch(Plane.XY) as sk:
            with Locations(*[(d["slot_x0"] + d["travel"] / 2, sy * d["screw_y"]) for sy in (-1, 1)]):
                SlotCenterToCenter(d["travel"], d["screw_bore"])
        extrude(sk.sketch, amount=d["foot_t"], mode=Mode.SUBTRACT)
    return bp.part - _groove(d, 0.0, d["z_l"] - d["track_top_z"], 1.0)


def place_jaw(d: dict, jaw: Part, w: float, t: float) -> Part:
    return jaw.moved(Location((jaw_face(d, w, t), 0, d["track_top_z"])))


def build_hardware(name: str, w: float, t: float) -> dict:
    """A board w wide and t thick in the clamp, its jaw screws, its underside
    tails, and the tile-to-base screws with their driver columns. Envelopes."""
    d = derive_clamp(name)
    e = engage(d, t)
    xm = jaw_face(d, w, t)
    Lb = d["board_l_max"]
    board = Box(w, Lb, t, align=ALIGN_MIN_Z).moved(Location((-e + w / 2, 0, d["z_l"])))
    k = d["edge_keepout"]
    tails = Box(w - 2 * k, Lb, d["underside_protrusion"], align=ALIGN_MIN_Z).moved(
        Location((-e + w / 2, 0, d["z_l"] - d["underside_protrusion"])))
    ztop = d["track_top_z"] + d["foot_t"]
    jaw_screws = [Cylinder(M3["d"] / 2, d["jaw_screw_len"], align=ALIGN_MIN_Z).moved(Location((x, y, ztop - d["jaw_screw_len"])))
                  + Cylinder(M3["head_dk"] / 2, M3["head_k"], align=ALIGN_MIN_Z).moved(Location((x, y, ztop)))
                  for x, y in d["inserts"]]
    mount, column = [], []
    for x, y in d["mount_holes"]:
        mount.append(Cylinder(M3["d"] / 2, d["plate_t"], align=ALIGN_MIN_Z).moved(Location((x, y, 0)))
                     + Cylinder(M3["head_dk"] / 2, M3["head_k"], align=ALIGN_MIN_Z).moved(Location((x, y, d["plate_t"]))))
        z0 = d["plate_t"] + M3["head_k"]
        column.append(Cylinder(M3["head_dk"] / 2, d["jaw_top_z"] + 5.0 - z0, align=ALIGN_MIN_Z).moved(Location((x, y, z0))))
    return dict(board=board, tails=tails, jaw_x=xm, jaw_screws=Compound(children=jaw_screws),
                mount_screws=Compound(children=mount), mount_columns=Compound(children=column))


def _seated(d, tile, jaw, hw, t) -> None:
    """The board touches both groove roofs and sits in neither jaw: moved 0.05 towards either jaw, it overlaps it."""
    b = hw["board"]
    assert interference_volume(b, tile) < 1e-6 and interference_volume(b, jaw) < 1e-6, "board inside a jaw"
    assert interference_volume(b.moved(Location((-0.05, 0, 0))), tile) > 1e-6, f"t {t}: board not against the fixed jaw roof"
    assert interference_volume(b.moved(Location((0.05, 0, 0))), jaw) > 1e-6, f"t {t}: board not against the sliding jaw roof"


def check_clamp(name: str, tile: Part, jaw: Part) -> dict:
    d = derive_clamp(name)
    label = f"clamp {name}"
    for p, what in ((tile, "tile"), (jaw, "jaw")):
        assert p.is_valid, f"{label}: {what} invalid"
        single_solid(p)
    assert_bbox(tile, (*d["tile_size"], d["jaw_top_z"]), 0.0, d["bbox_tol"], f"{label} tile")
    assert_bbox(jaw, (d["foot_len"], d["jaw_len"], d["jaw_top_z"] - d["track_top_z"]), 0.0, d["bbox_tol"], f"{label} jaw")
    g, b, zl = d["groove_depth"], d["groove_back"], d["z_l"]
    probes = {
        "groove floor": ((-g / 2, 0, zl - 0.05), True),
        "groove air": ((-g / 2, 0, zl + 0.05), False),
        "groove back wall": ((-g - 0.05, 0, zl + b / 2), True),
        "roof air below": ((-0.3, 0, zl + b + g - 0.3 - 0.1), False),
        "roof solid above": ((-0.3, 0, zl + b + g - 0.3 + 0.1), True),
        "track": ((d["track_x"][0] + 0.5, 0, d["track_top_z"] - 0.1), True),
        "above track": ((d["track_x"][0] + 0.5, 0, d["track_top_z"] + 0.1), False),
    }
    for i, (x, y) in enumerate(d["inserts"]):
        probes[f"insert{i} bore"] = ((x, y, d["track_top_z"] - 0.1), False)
        probes[f"insert{i} floor"] = ((x, y, d["track_top_z"] - d["insert_bore_depth"] - 0.05), True)
    for i, (x, y) in enumerate(d["mount_holes"]):
        probes[f"mount{i} bore"] = ((x, y, d["plate_t"] / 2), False)
    for i, (x, y) in enumerate(d["ties"]):
        probes[f"tie{i} slot"] = ((x, y, d["plate_t"] / 2), False)
    assert_material(tile, probes)
    jz = zl - d["track_top_z"]
    assert_material(jaw, {
        "jaw groove floor": ((g / 2, 0, jz - 0.05), True),
        "jaw groove air": ((g / 2, 0, jz + 0.05), False),
        **{f"jaw slot{i}": ((d["slot_x0"] + f * d["travel"], sy * d["screw_y"], d["foot_t"] / 2), False)
           for i, (f, sy) in enumerate(((0, -1), (1, -1), (0, 1), (1, 1)))},
        "jaw foot beside slot": ((d["slot_x0"], d["screw_y"] + d["screw_bore"] / 2 + 0.3, d["foot_t"] / 2), True),
    })
    # function: every corner of the board range clamps, and nothing collides at either end of the travel
    for w in d["board_w"]:
        for t in d["board_t"]:
            hw = build_hardware(name, w, t)
            pj = place_jaw(d, jaw, w, t)
            _seated(d, tile, pj, hw, t)
            assert interference_volume(pj, tile) < 1e-6, f"{label}: w {w} t {t}: jaw inside the tile"
            for part, what in ((tile, "tile"), (pj, "jaw")):
                assert interference_volume(hw["tails"], part) < 1e-6, f"{label}: w {w} t {t}: board tails hit the {what}"
                assert interference_volume(hw["jaw_screws"], part) < 1e-6, f"{label}: w {w} t {t}: a jaw screw hits the {what}"
                assert interference_volume(hw["mount_screws"], part) < 1e-6, f"{label}: w {w} t {t}: a base screw hits the {what}"
                assert interference_volume(hw["mount_columns"], part) < 1e-6, \
                    f"{label}: w {w} t {t}: no straight-down driver path to a base screw past the {what}"
            # the foot rests on the track over its whole length
            fx0 = hw["jaw_x"]
            assert d["track_x"][0] - 1e-6 <= fx0 and fx0 + d["foot_len"] <= d["track_x"][1] + 1e-6, f"{label}: foot off the track"
            assert is_inside(tile, (fx0 + 0.1, 0, d["track_top_z"] - 0.05)), f"{label}: no track under the jaw face"
    # the jaw screw passes the whole insert and stops above the bore floor
    tip = d["track_top_z"] + d["foot_t"] - d["jaw_screw_len"]
    floor = d["track_top_z"] - d["insert_bore_depth"]
    assert tip <= d["track_top_z"] - INSERT["length"] + 1e-9 and tip >= floor + d["insert_tip_clear"] - 1e-9, f"{label}: jaw screw tip {tip:.2f}"
    return dict(tile_volume=tile.volume, jaw_volume=jaw.volume, tile_bbox=tile.bounding_box().size,
                jaw_bbox=jaw.bounding_box().size)


result = build_tile(ACTIVE_CLAMPS[0])

if __name__ == "__main__":
    from cacad import export, export_3mf
    OUT = __file__.rsplit("/", 1)[0] + "/out"   # a string: the MCP sandbox rejects os/pathlib/sys in this file (F23)
    for name in ACTIVE_CLAMPS:
        tile, jaw = build_tile(name), build_jaw(name)
        rep = check_clamp(name, tile, jaw)
        tb, jb = rep["tile_bbox"], rep["jaw_bbox"]
        print(f"clamp {name}: tile {tb.X:.2f} x {tb.Y:.2f} x {tb.Z:.2f}, jaw {jb.X:.2f} x {jb.Y:.2f} x {jb.Z:.2f}, "
              f"volumes {rep['tile_volume']:.1f} + {rep['jaw_volume']:.1f}")
        export(tile, f"module_grid_clamp_{name}_tile", OUT)
        export(jaw, f"module_grid_clamp_{name}_jaw", OUT)
        export_3mf({f"clamp_{name}_tile": tile, f"clamp_{name}_jaw": jaw.moved(Location((0, -45, 0)))},
                   OUT + f"/module_grid_clamp_{name}.3mf")
