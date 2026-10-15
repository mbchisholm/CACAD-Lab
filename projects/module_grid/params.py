"""module_grid: a 20 mm grid that boards, sensors and actuators mount to as
tiles. A printed base carries an M3 heat-set insert bore at every cell centre,
and a tile is n x m cells with an M3 clearance hole at the centre of each corner
cell, so any tile screws to any base at any cell. Inserts go in only where a
tile needs one.

Two kinds of tile:
- a standoff_plate row with `mount=dict(..., grid=True)`: a board with known
  holes on bosses with captured nuts (SURVEYOR_PH_tile);
- an edge clamp (this file, CLAMPS): a board whose holes are unpublished
  (generic DS18B20 screw-terminal adapters), gripped by two grooved jaws, one
  fixed and one sliding on two M3 screws in heat-set inserts.

Fasteners: M3 heat-set inserts where a joint is made and unmade (tile to base,
the clamp jaw). The board screws stay M2 / M2.5 into captured nuts: the boards'
holes take nothing larger, no M2 insert is on hand, and the first print's
failure was the boss geometry, not the nut (docs/PRINT_LOG.md 2026-10-15).

Axis convention: Z up, Z=0 the bed face of each printed part. Base: plate on
the bed, ribs and insert bosses up; tiles rest on the boss tops.

    .venv/bin/python projects/module_grid/params.py      # prints the design
"""
from __future__ import annotations

import math
from types import MappingProxyType

from cacad.registries.materials import (INSERT_BORE_M3, INSERT_LEN_M3, INSERT_WALL_M3, LAYER, NOZZLE, WALL,
                                        clearance_bore)

STATUS = "passes"   # concept | passes | printed | parked

# ---------------------------------------------------------------------------
# The grid every tile and base shares.
# ---------------------------------------------------------------------------
GRID = MappingProxyType(dict(
    pitch=20.0,       # DESIGN: the 2020 extrusion module (nft_table), so a base can also sit on a 2020 frame
    tile_gap=0.4,     # DESIGN: a tile is n * pitch - tile_gap, so neighbours never touch (one nozzle width)
    screw="M3",       # tile to base and the clamp jaw: ISO 4762 M3 into a heat-set insert
))

# ISO 4762 M3 socket head cap screw: head dk 5.5, k 3.0; the stocked ladder (as standoff_plate.SCREWS)
M3 = MappingProxyType(dict(d=3.0, head_dk=5.5, head_k=3.0, lengths=(5, 6, 8, 10, 12, 16, 20, 25)))

# M3 heat-set insert, CNC Kitchen standard (materials.py): bore 4.0, length 5.7, wall 1.6 minimum.
INSERT = MappingProxyType(dict(bore=INSERT_BORE_M3, length=INSERT_LEN_M3, wall=INSERT_WALL_M3))

COMMON = MappingProxyType(dict(
    # --- named clearances (mm) ---
    insert_tip_clear=0.4,     # screw tip to insert bore floor. DESIGN
    insert_floor=1.2,         # insert bore floor to the bed face, 6 layers (min_wall). DESIGN
    head_clear=0.5,           # plan: screw head edge to anything beside it (a driver goes straight down). DESIGN
    # --- geometry rules ---
    wall=WALL,                # 4 perimeters
    corner_r=2.0,             # vertical corner radius of a base or tile
    # --- manufacturing rules ---
    nozzle_d=NOZZLE,
    layer=LAYER,
    min_wall=1.2,
    max_overhang_deg=60.0,
    bbox_tol=0.05,
))


def _round_up(x: float, step: float) -> float:
    return round(math.ceil(x / step - 1e-9) * step, 6)


def insert_bore_depth() -> float:
    """Every M3 insert bore in the grid has one depth: the insert, one step of the
    stocked screw ladder past it, and the tip clearance. Then any clamp
    thickness has a stocked screw that passes fully through the insert and stops
    short of the floor."""
    step = max(b - a for a, b in zip(M3["lengths"], M3["lengths"][1:]) if 8 <= a and b <= 12)   # 2 mm: 8, 10, 12
    return _round_up(INSERT["length"] + step + COMMON["insert_tip_clear"], COMMON["layer"])


def insert_screw(clamp: float) -> int:
    """Shortest stocked M3 that passes clamp + the whole insert and stops
    insert_tip_clear above the bore floor."""
    lo, hi = clamp + INSERT["length"], clamp + insert_bore_depth() - COMMON["insert_tip_clear"]
    fit = [L for L in M3["lengths"] if lo - 1e-9 <= L <= hi + 1e-9]
    assert fit, f"no stocked M3 for clamp {clamp:.2f}: needs {lo:.2f}..{hi:.2f}"
    return fit[0]


def grid_size(extent: float) -> tuple[int, float]:
    """Cells and tile length for something at least `extent` long."""
    n = max(1, math.ceil((extent + GRID["tile_gap"]) / GRID["pitch"] - 1e-9))
    return n, n * GRID["pitch"] - GRID["tile_gap"]


def corner_inset() -> float:
    """Tile edge to the centre of its corner cell: where its mount holes are."""
    return GRID["pitch"] / 2 - GRID["tile_gap"] / 2


PRINT_ORIENTATION = MappingProxyType(dict(
    base=dict(up=(0, 0, 1), bed_face="back plate", bed_z="0", known_overhangs=[], overhang_exceptions=[]),
    # the jaw grooves' roofs are 45 deg from vertical: inside max_overhang_deg, no exception
    clamp_tile=dict(up=(0, 0, 1), bed_face="tile plate", bed_z="0", known_overhangs=[], overhang_exceptions=[]),
    clamp_jaw=dict(up=(0, 0, 1), bed_face="jaw foot", bed_z="0", known_overhangs=[], overhang_exceptions=[]),
))

# ---------------------------------------------------------------------------
# Bases. Inputs only.
# ---------------------------------------------------------------------------
BASES = {
    # 160 x 120: room for the Surveyor tile (3 x 3), a DS18B20 clamp (3 x 3) and a 2-cell strip. Fits the A1 bed.
    "B8x6": dict(cells=(8, 6),
                 plate_t=3.0,          # DESIGN: back plate; the ribs carry the stiffness
                 cable_gap=3.0,        # DESIGN: rib top to tile underside, room for jumpers under a tile
                 wall_screw="M4",      # #8 pan-head wood screw (4.17, head 7.9) or M4 ISO 7045 (dk 8.0, k 3.1)
                 wall_head=(8.0, 3.1),
                 # wall screws at the grid nodes one cell in from each corner, between the ribs
                 wall_nodes=((1, 1), (7, 1), (1, 5), (7, 5))),
}
ACTIVE_BASES = ("B8x6",)

# ---------------------------------------------------------------------------
# Edge clamps. A board with no published hole pattern is gripped by two of its
# opposite edges in 45 deg grooves: one jaw printed with the tile, one sliding
# on two M3 screws in heat-set inserts. The board's top corner meets the
# groove roof, so the jaw presses the edge down onto the groove floor and the
# clamp takes any width in the range and any thickness the groove admits.
# ---------------------------------------------------------------------------
CLAMPS = {
    # DS18B20 screw-terminal adapters (4.7k pull-up, 3-way terminal for the probe, 3-pin header). No vendor publishes
    # an outline or holes. Listed outlines: 24 x 21 (sigmanortec.ro, UNVERIFIED), Adafruit chainable extender
    # 25.3 x 18.0 (Adafruit). Grip the two edges that carry neither the terminal nor the header.
    "DS18B20": dict(
        board_w=(16.0, 28.0),          # DESIGN: clamped width range, covers both listed outlines either way round
        board_l_max=30.0,              # DESIGN: length along the jaws the tile keeps clear (boards overhang the jaws)
        board_t=(1.0, 1.7),            # PCB thickness the groove grips; 1.6 typical. UNVERIFIED for generic boards
        edge_keepout=1.5,              # bare strip along each gripped edge, top and bottom: covers the deepest
                                       # engagement (1.4, a 1.0 board). UNVERIFIED for generic boards
        underside_protrusion=3.5,      # DESIGN allowance: trimmed terminal and header tails (as standoff_plate)
        board_air_gap=1.0,             # tail tip to the track or plate below
        groove_depth=1.8,              # DESIGN: into the jaw; a 1.6 board's edge sits 0.8 in, a 1.0 board's 1.4
        jaw_w=4.5,                     # DESIGN: jaw body, face to back; leaves 2.5 behind the groove
        jaw_len=18.0,                  # DESIGN: grip length along the edge; holds two inserts with their walls
        screw_y=5.0,                   # DESIGN: jaw screws at +-5 along the jaw
        foot_t=3.0,                    # DESIGN: sliding jaw foot under the screw heads (the clamp)
        plate_t=3.0,                   # DESIGN: tile plate
        lip=1.2,                       # jaw material above the groove roof (min_wall)
        tie=(2.0, 4.0, 10.0),          # DESIGN: zip-tie slots (x, y) and their centre spacing; ties up to 3.6 wide
        tie_gap=3.0,                   # board end (at board_l_max) to the tie slots
    ),
}
ACTIVE_CLAMPS = ("DS18B20",)

# ---------------------------------------------------------------------------
# Layouts: tiles on a base, each (kind, name, (i, j)) with (i, j) its lower-left cell. kind "plate" is a
# standoff_plate row with a grid mount, "clamp" a CLAMPS row.
# ---------------------------------------------------------------------------
LAYOUTS = {
    # the probe end of the nutrient node: Surveyor pH top left, its SMA off the base's -X edge; two DS18B20 clamps
    # along the bottom, their probe cables and zip ties off the -Y edge. Cells 6..7 are free for the next tile.
    "PROBES": dict(base="B8x6", tiles=(("plate", "SURVEYOR_PH_tile", (0, 3)),
                                       ("clamp", "DS18B20", (0, 0)),
                                       ("clamp", "DS18B20", (3, 0)))),
}
ACTIVE_LAYOUTS = ("PROBES",)


def derive_base(name: str, **overrides) -> dict:
    s = dict(BASES[name])
    c = dict(COMMON)
    for k, v in overrides.items():
        (s if k in s else c)[k] = v
    d = dict(base=name, **s, **c, pitch=GRID["pitch"])
    nx, ny = s["cells"]
    p = GRID["pitch"]
    d["size"] = (nx * p, ny * p)                      # a base is whole cells; tiles are tile_gap short of theirs
    d["insert_bore_d"] = INSERT["bore"]
    d["insert_bore_depth"] = insert_bore_depth()
    d["boss_r"] = INSERT["bore"] / 2 + INSERT["wall"]
    d["boss_top_z"] = _round_up(max(s["plate_t"] + c["layer"], d["insert_bore_depth"] + c["insert_floor"]), c["layer"])
    d["rib_w"] = c["wall"]
    d["rib_top_z"] = round(d["boss_top_z"] - s["cable_gap"], 6)
    d["rim_w"] = c["wall"]
    x0, y0 = -nx * p / 2, -ny * p / 2
    d["inserts"] = [(x0 + (i + 0.5) * p, y0 + (j + 0.5) * p) for i in range(nx) for j in range(ny)]
    d["rib_x"] = [x0 + (i + 0.5) * p for i in range(nx)]   # ribs along Y at these x
    d["rib_y"] = [y0 + (j + 0.5) * p for j in range(ny)]   # ribs along X at these y
    d["wall_holes"] = [(x0 + i * p, y0 + j * p) for i, j in s["wall_nodes"]]
    d["wall_bore_d"] = clearance_bore(s["wall_screw"])
    d["wall_head_r"] = s["wall_head"][0] / 2
    d["print_orientation"] = {k: dict(v, bed_z=float(v["bed_z"])) for k, v in PRINT_ORIENTATION.items()}
    half = p / 2
    d["walls"] = {
        "insert boss wall": INSERT["wall"],
        "rib": d["rib_w"],
        "rim": d["rim_w"],
        "insert floor": d["boss_top_z"] - d["insert_bore_depth"],
        "plate between ribs": s["plate_t"],
        # wall-screw bore to the nearest rib face (nodes sit midway between ribs)
        "wall bore to rib": half - d["rib_w"] / 2 - d["wall_bore_d"] / 2,
    }
    return d


def validate_base(name: str) -> dict:
    d = derive_base(name)
    for k, w in d["walls"].items():
        w = round(w, 6)
        assert w >= d["min_wall"], f"{name}: wall {k} = {w:.2f} < {d['min_wall']}"
        assert w >= 2 * d["nozzle_d"], f"{name}: wall {k} = {w:.2f} < 2 x nozzle"
    assert d["rib_top_z"] > d["plate_t"] + d["layer"], f"{name}: cable gap leaves no rib"
    assert d["boss_r"] * 2 < d["pitch"], f"{name}: insert bosses merge"
    p = d["pitch"]
    for x, y in d["wall_holes"]:
        # head lies flat on the plate between the ribs and below the tiles, clear of the bosses
        assert abs(x) < d["size"][0] / 2 and abs(y) < d["size"][1] / 2, f"{name}: wall node ({x}, {y}) off the base"
        to_rib = p / 2 - d["rib_w"] / 2
        assert d["wall_head_r"] + d["head_clear"] <= to_rib, f"{name}: wall screw head reaches a rib"
        to_boss = min(math.dist((x, y), b) for b in d["inserts"]) - d["boss_r"]
        assert d["wall_head_r"] + d["head_clear"] <= to_boss, f"{name}: wall screw head reaches an insert boss"
        assert d["plate_t"] + d["wall_head"][1] <= d["boss_top_z"] - d["layer"], f"{name}: wall screw head stands above the tiles' seat"
    bx, by = d["size"]
    assert bx <= 256 and by <= 256, f"{name}: base {bx} x {by} over the A1 bed"
    return d


def engage(d: dict, t: float) -> float:
    """How far a board t thick goes into a groove before its top corner meets the roof."""
    return round(d["groove_depth"] - (t - d["groove_back"]), 6)


def jaw_face(d: dict, w: float, t: float) -> float:
    """Sliding jaw face x for a board w wide and t thick: each edge sits engage() into its groove."""
    return w - 2 * engage(d, t)


def derive_clamp(name: str, **overrides) -> dict:
    """Tile frame: the fixed jaw's face at x = 0, the board extends +X from it,
    the sliding jaw's face looks -X. Y = 0 is the jaws' mid-length."""
    s = dict(CLAMPS[name])
    c = dict(COMMON)
    for k, v in overrides.items():
        (s if k in s else c)[k] = v
    d = dict(clamp=name, **s, **c)
    t_min, t_max = s["board_t"]
    w_min, w_max = s["board_w"]
    # groove: floor at z_l, a vertical back wall `back` tall at depth groove_depth, a 45 deg roof back out to the face
    d["groove_back"] = round(t_min - 2 * c["layer"], 6)      # under the thinnest board, so its top corner meets the roof
    d["engage"] = {t: engage(d, t) for t in s["board_t"]}   # edge into the groove, thinnest and thickest board
    d["groove_top"] = d["groove_back"] + s["groove_depth"]   # roof meets the face this far above the floor
    d["x_m_min"] = min(jaw_face(d, w_min, t) for t in s["board_t"])
    d["x_m_max"] = max(jaw_face(d, w_max, t) for t in s["board_t"])
    d["travel"] = d["x_m_max"] - d["x_m_min"]
    # jaw screws: fixed in inserts in the track; slots in the foot run along X
    d["screw_bore"] = clearance_bore(GRID["screw"])
    d["head_r"] = M3["head_dk"] / 2
    d["slot_x0"] = s["jaw_w"] + d["head_r"] + c["head_clear"]           # foot-local x of the screw at x_m_max
    d["slot_len"] = d["travel"] + d["screw_bore"]                        # end to end
    d["foot_len"] = round(d["slot_x0"] + d["travel"] + d["head_r"] + c["wall"], 6)
    d["insert_x"] = d["x_m_max"] + d["slot_x0"]
    d["inserts"] = [(d["insert_x"], sy * s["screw_y"]) for sy in (-1, 1)]
    d["insert_bore_depth"] = insert_bore_depth()
    d["jaw_screw_len"] = insert_screw(s["foot_t"])
    # heights: the track holds the insert bores; the board's tails clear the track (it runs under wide boards)
    d["track_top_z"] = _round_up(max(s["plate_t"] + c["layer"], d["insert_bore_depth"] + c["insert_floor"]), c["layer"])
    d["z_l"] = _round_up(max(d["track_top_z"] + s["underside_protrusion"] + s["board_air_gap"],
                             d["track_top_z"] + s["foot_t"] + c["min_wall"]), c["layer"])
    d["jaw_top_z"] = _round_up(d["z_l"] + d["groove_top"] + s["lip"], c["layer"])
    d["track_x"] = (d["x_m_min"], d["x_m_max"] + d["foot_len"])
    d["track_y"] = s["jaw_len"]
    # footprint of everything standing on the tile plate (jaws, track, tie slots), then the grid tile around it with
    # mount holes in the corner cells. The board, 14 mm up, may overhang a mount head: the tile goes on the base first.
    fx0, fx1 = -s["jaw_w"], d["track_x"][1]
    fy = s["jaw_len"] / 2
    d["board_cx"] = jaw_face(d, sum(s["board_w"]) / 2, max(s["board_t"])) / 2   # board centre at mid-range width
    tx, ty, tsp = s["tie"]
    d["tie_y"] = -(s["board_l_max"] / 2 + s["tie_gap"] + ty / 2)
    d["ties"] = [(d["board_cx"] + sx * tsp / 2, d["tie_y"]) for sx in (-1, 1)]
    fy0 = min(-fy, d["tie_y"] - ty / 2)
    inset = corner_inset()
    keep = d["head_r"] + c["head_clear"]
    # smallest tile (cells) whose corner-cell holes all sit outside the footprint by a head radius + clearance
    best = None
    for nx in range(1, 13):
        for ny in range(1, 13):
            W, H = nx * GRID["pitch"] - GRID["tile_gap"], ny * GRID["pitch"] - GRID["tile_gap"]
            cx, cy = (fx0 + fx1) / 2, (fy0 + fy) / 2
            if W < fx1 - fx0 + 2 * c["min_wall"] or H < fy - fy0 + 2 * c["min_wall"]:   # plate beyond the footprint
                continue
            holes = [(cx + sx * (W / 2 - inset), cy + sy * (H / 2 - inset)) for sx in (-1, 1) for sy in (-1, 1)]
            ok = all(x < fx0 - keep or x > fx1 + keep or y < fy0 - keep or y > fy + keep for x, y in holes)
            if ok and (best is None or nx * ny < best[0] * best[1]):
                best = (nx, ny, W, H, cx, cy, holes)
    assert best, f"{name}: no tile up to 12 x 12 cells clears its mount holes"
    nx, ny, W, H, cx, cy, holes = best
    d["cells"], d["tile_size"], d["tile_centre"], d["mount_holes"] = (nx, ny), (W, H), (cx, cy), holes
    d["tile_x"] = (cx - W / 2, cx + W / 2)
    d["tile_y"] = (cy - H / 2, cy + H / 2)
    d["footprint"] = ((fx0, fx1), (fy0, fy))
    d["mount_screw_len"] = insert_screw(s["plate_t"])   # tile to base
    d["print_orientation"] = {k: dict(v, bed_z=float(v["bed_z"])) for k, v in PRINT_ORIENTATION.items()}
    d["walls"] = {
        "jaw behind groove": s["jaw_w"] - s["groove_depth"],
        "lip above roof": d["jaw_top_z"] - d["z_l"] - d["groove_top"],
        "groove floor above foot": d["z_l"] - d["track_top_z"] - s["foot_t"],
        "insert wall in track (y)": s["jaw_len"] / 2 - s["screw_y"] - INSERT["bore"] / 2,
        "insert floor": d["track_top_z"] - d["insert_bore_depth"],
        "slot to foot edge (y)": s["jaw_len"] / 2 - s["screw_y"] - d["screw_bore"] / 2,
        "foot end past slot": d["foot_len"] - d["slot_x0"] - d["travel"] - d["screw_bore"] / 2,
        "foot": s["foot_t"],
        "tile plate": s["plate_t"],
    }
    return d


def validate_clamp(name: str) -> dict:
    d = derive_clamp(name)
    for k, w in d["walls"].items():
        w = round(w, 6)
        assert w >= d["min_wall"], f"{name}: wall {k} = {w:.2f} < {d['min_wall']}"
        assert w >= 2 * d["nozzle_d"], f"{name}: wall {k} = {w:.2f} < 2 x nozzle"
    t_min, t_max = d["board_t"]
    # every thickness meets the roof inside the groove and leaves the edge in it by at least a nozzle width
    for t, e in d["engage"].items():
        assert d["nozzle_d"] <= e < d["groove_depth"], f"{name}: a {t} board engages {e:.2f} of a {d['groove_depth']} groove"
        assert e <= d["edge_keepout"], f"{name}: a {t} board's edge goes {e:.2f} into the jaw, keepout {d['edge_keepout']}"
    assert d["groove_back"] < t_min, f"{name}: the thinnest board bottoms on the groove back wall"
    # head on the foot: clear of the jaw body at the widest setting, inside the foot at the narrowest
    assert d["slot_x0"] - d["head_r"] >= d["jaw_w"] + d["head_clear"] - 1e-9, f"{name}: jaw screw head under the jaw body"
    assert d["screw_y"] + d["head_r"] <= d["jaw_len"] / 2 + 1e-9, f"{name}: jaw screw head off the foot"
    assert 2 * d["screw_y"] - 2 * d["head_r"] >= d["head_clear"], f"{name}: jaw screw heads touch"
    # a stocked screw passes the whole insert and stops above the floor (insert_screw asserts it)
    tx, ty, _ = d["tie"]
    for x, y in d["ties"]:
        for hx, hy in d["mount_holes"]:
            assert abs(x - hx) > tx / 2 + d["head_r"] + d["head_clear"] or abs(y - hy) > ty / 2 + d["head_r"] + d["head_clear"], \
                f"{name}: zip-tie slot at ({x:.1f}, {y:.1f}) under a mount screw head"
        assert d["tile_y"][0] + d["wall"] <= y - ty / 2, f"{name}: zip-tie slot runs off the tile"
    W, H = d["tile_size"]
    assert W <= 256 and H <= 256
    return d


def derive_layout(name: str) -> dict:
    """Each tile's offset from its own frame to the base frame, its cells, outline and mount holes in the base frame."""
    from projects.standoff_plate.params import derive as derive_plate   # standoff_plate imports this module
    s = LAYOUTS[name]
    base = derive_base(s["base"])
    p = GRID["pitch"]
    bx0, by0 = -base["size"][0] / 2, -base["size"][1] / 2
    tiles = []
    for kind, tname, (i, j) in s["tiles"]:
        if kind == "plate":
            t = derive_plate(tname)
            cells, size, centre, holes = t["grid_cells"], t["plate_size"], t["plate_centre"], t["mount_holes"]
            screw_len, top = t["mount_screw_len"], t["z_head_top"]
        else:
            t = derive_clamp(tname)
            cells, size, centre, holes = t["cells"], t["tile_size"], t["tile_centre"], t["mount_holes"]
            screw_len, top = t["mount_screw_len"], t["jaw_top_z"]
        target = (bx0 + (i + cells[0] / 2) * p, by0 + (j + cells[1] / 2) * p)
        off = (target[0] - centre[0], target[1] - centre[1], base["boss_top_z"])
        tiles.append(dict(kind=kind, name=tname, cell=(i, j), cells=cells, size=size, offset=off,
                          x=(target[0] - size[0] / 2, target[0] + size[0] / 2), y=(target[1] - size[1] / 2, target[1] + size[1] / 2),
                          holes=[(x + off[0], y + off[1]) for x, y in holes], screw_len=screw_len, height=top))
    return dict(layout=name, base=base, tiles=tiles)


def validate_layout(name: str) -> dict:
    d = derive_layout(name)
    base = d["base"]
    sx, sy = base["size"]
    inserts = base["inserts"]
    for t in d["tiles"]:
        i, j = t["cell"]
        nx, ny = t["cells"]
        assert 0 <= i and i + nx <= base["cells"][0] and 0 <= j and j + ny <= base["cells"][1], f"{name}: {t['name']} off the base"
        for h in t["holes"]:
            assert min(math.dist(h, b) for b in inserts) < 1e-6, f"{name}: {t['name']} mount hole {h} misses every insert"
    for a in range(len(d["tiles"])):
        for b in range(a + 1, len(d["tiles"])):
            ta, tb = d["tiles"][a], d["tiles"][b]
            gap = max(tb["x"][0] - ta["x"][1], ta["x"][0] - tb["x"][1], tb["y"][0] - ta["y"][1], ta["y"][0] - tb["y"][1])
            assert gap >= GRID["tile_gap"] - 1e-6, f"{name}: {ta['name']} and {tb['name']} overlap ({gap:.2f})"
    return d


def report_base(name: str) -> str:
    d = derive_base(name)
    return "\n".join([
        f"{name}: {d['cells'][0]} x {d['cells'][1]} cells, {d['size'][0]:.0f} x {d['size'][1]:.0f} x {d['boss_top_z']:.2f}",
        f"  {len(d['inserts'])} insert bores dia {d['insert_bore_d']:.2f} x {d['insert_bore_depth']:.2f} deep in bosses dia "
        f"{2 * d['boss_r']:.2f}; tiles seat at z {d['boss_top_z']:.2f}",
        f"  ribs {d['rib_w']:.2f} wide to z {d['rib_top_z']:.2f} ({d['cable_gap']:.1f} under the tiles), plate {d['plate_t']:.2f}",
        f"  {len(d['wall_holes'])} wall screws {d['wall_screw']} / #8 pan head, bore {d['wall_bore_d']:.2f}, at grid nodes",
    ])


def report_clamp(name: str) -> str:
    d = derive_clamp(name)
    return "\n".join([
        f"{name} clamp tile: {d['cells'][0]} x {d['cells'][1]} cells, {d['tile_size'][0]:.1f} x {d['tile_size'][1]:.1f} x {d['jaw_top_z']:.2f}",
        f"  boards {d['board_w'][0]:.0f}..{d['board_w'][1]:.0f} wide, {d['board_t'][0]}..{d['board_t'][1]} thick, "
        f"edge in the groove {min(d['engage'].values()):.2f}..{max(d['engage'].values()):.2f}; board underside at z {d['z_l']:.2f}",
        f"  sliding jaw: foot {d['foot_len']:.1f} x {d['jaw_len']:.1f} x {d['foot_t']:.1f}, travel {d['travel']:.2f}, "
        f"2 x M3 x {d['jaw_screw_len']} into inserts in the track (top z {d['track_top_z']:.2f})",
        f"  to the base: 4 x M3 x {d['mount_screw_len']}; zip-tie slots at y {d['tie_y']:.1f}",
    ])


if __name__ == "__main__":
    print(f"grid {GRID['pitch']:.0f} mm, tile = n x {GRID['pitch']:.0f} - {GRID['tile_gap']}, mount holes {corner_inset():.1f} "
          f"from tile edges; M3 insert bore {INSERT['bore']:.1f} x {insert_bore_depth():.2f}")
    for fam, val, rep, active in ((BASES, validate_base, report_base, ACTIVE_BASES),
                                  (CLAMPS, validate_clamp, report_clamp, ACTIVE_CLAMPS)):
        for name in fam:
            try:
                val(name)
                print(rep(name), "\n  ok" + ("" if name in active else " (inactive)"))
            except AssertionError as e:
                print(f"{name}: FAIL: {e}")
    for name in LAYOUTS:
        try:
            d = validate_layout(name)
            print(f"layout {name} on {d['base']['base']}:")
            for t in d["tiles"]:
                print(f"  {t['kind']} {t['name']} at cell {t['cell']}, {t['cells'][0]} x {t['cells'][1]} cells, "
                      f"{len(t['holes'])} x M3 x {t['screw_len']} into inserts")
            used = sorted({b for t in d["tiles"] for b in t["holes"]})
            print(f"  {len(used)} inserts to fit of {len(d['base']['inserts'])} bores\n  ok")
        except AssertionError as e:
            print(f"layout {name}: FAIL: {e}")
