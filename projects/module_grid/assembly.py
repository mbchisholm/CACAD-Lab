"""module_grid layouts: tiles on a base, with the boards, the jaws at a
nominal board width and the screws, checked pairwise (F7) and exported as
one STEP; plus the print set, one 3MF per bed.

    .venv/bin/python projects/module_grid/assembly.py     # ACTIVE_LAYOUTS -> out/
"""
from __future__ import annotations

from build123d import Compound, Cylinder, Location, Part

from cacad import ALIGN_MIN_Z, interference_volume
from projects.module_grid.base import build_base
from projects.module_grid.clamp import build_hardware as clamp_hardware, build_jaw, build_tile, place_jaw
from projects.module_grid.params import ACTIVE_LAYOUTS, INSERT, M3, derive_clamp, derive_layout
from projects.standoff_plate.plate import build_hardware as plate_hardware, build_plate

NOMINAL = dict(w=24.0, t=1.6)   # a board in each clamp for the picture and the collision check: the listed 24 x 21 outline


def build_layout(name: str) -> dict:
    d = derive_layout(name)
    base = build_base(d["base"]["base"])
    parts = {"base": base}
    for k, t in enumerate(d["tiles"]):
        loc = Location(t["offset"])
        tag = f"{k}_{t['name']}"
        if t["kind"] == "plate":
            parts[f"tile{tag}"] = build_plate(t["name"]).moved(loc)
            hw = plate_hardware(t["name"])
            parts[f"board{tag}"] = hw["boards"].moved(loc)
            parts[f"screws{tag}"] = Compound(children=[hw["screws"], hw["nuts"]]).moved(loc)
        else:
            cd = derive_clamp(t["name"])
            parts[f"tile{tag}"] = build_tile(t["name"]).moved(loc)
            parts[f"jaw{tag}"] = place_jaw(cd, build_jaw(t["name"]), NOMINAL["w"], NOMINAL["t"]).moved(loc)
            hw = clamp_hardware(t["name"], NOMINAL["w"], NOMINAL["t"])
            parts[f"board{tag}"] = hw["board"].moved(loc)
            parts[f"screws{tag}"] = hw["jaw_screws"].moved(loc)
        # tile to base: M3 through the tile plate into the insert below, head on the tile plate top
        z_seat = d["base"]["boss_top_z"]
        parts[f"basescrews{tag}"] = Compound(children=[
            Cylinder(M3["d"] / 2, t["screw_len"], align=ALIGN_MIN_Z).moved(Location((x, y, z_seat + _clamp(t) - t["screw_len"])))
            for x, y in t["holes"]])
    return dict(derive=d, parts=parts)


def _clamp(t: dict) -> float:
    """Tile plate thickness under the base screw head."""
    if t["kind"] == "plate":
        from projects.standoff_plate.params import derive
        return derive(t["name"])["plate_t"]
    return derive_clamp(t["name"])["plate_t"]


def check_layout(name: str, built: dict) -> None:
    d, parts = built["derive"], built["parts"]
    base = d["base"]
    names = list(parts)
    # pairwise: nothing occupies anything else's space (screws sit in bores, nuts in pockets, boards on bosses, tiles on
    # the insert bosses); touching is allowed
    for a in range(len(names)):
        for b in range(a + 1, len(names)):
            na, nb = names[a], names[b]
            v = interference_volume(parts[na], parts[nb])
            assert v < 1e-6, f"layout {name}: {na} and {nb} overlap by {v:.4f} mm^3"
    # every base screw passes the whole insert and stops above its bore floor
    for t in d["tiles"]:
        tip = base["boss_top_z"] + _clamp(t) - t["screw_len"]
        assert tip <= base["boss_top_z"] - INSERT["length"] + 1e-9, f"layout {name}: {t['name']} screw ends inside the insert"
        assert tip >= base["boss_top_z"] - base["insert_bore_depth"] + base["insert_tip_clear"] - 1e-9, \
            f"layout {name}: {t['name']} screw bottoms in the bore"


result = None

if __name__ == "__main__":
    from cacad import export, export_3mf
    OUT = __file__.rsplit("/", 1)[0] + "/out"   # a string: the MCP sandbox rejects os/pathlib/sys in this file (F23)
    for name in ACTIVE_LAYOUTS:
        built = build_layout(name)
        check_layout(name, built)
        parts = built["parts"]
        bb = Compound(children=list(parts.values())).bounding_box()
        print(f"layout {name}: {len(parts)} bodies, bbox {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f}, pairwise clear")
        export(Compound(children=[p.moved(Location((0, 0, 0))) for p in parts.values()]), f"module_grid_{name}_assembly", OUT)
        # print set: the base on one bed, every tile and jaw on a second
        d = built["derive"]
        export_3mf({"base": parts["base"]}, OUT + f"/module_grid_{name}_bed1_base.3mf")
        bed2, x = {}, 0.0
        for k, t in enumerate(d["tiles"]):
            tile = parts[f"tile{k}_{t['name']}"].moved(Location((-t["offset"][0], -t["offset"][1], -t["offset"][2])))
            bbt = tile.bounding_box()
            bed2[f"tile{k}_{t['name']}"] = tile.moved(Location((x - bbt.min.X, -bbt.min.Y, 0)))
            x += bbt.size.X + 5.0
            if t["kind"] == "clamp":
                jaw = build_jaw(t["name"])
                bbj = jaw.bounding_box()
                bed2[f"jaw{k}_{t['name']}"] = jaw.moved(Location((x - bbt.size.X - 5.0 - bbj.min.X, bbt.size.Y + 5.0 - bbj.min.Y, 0)))
        export_3mf(bed2, OUT + f"/module_grid_{name}_bed2_tiles.3mf")
        bb2 = Compound(children=list(bed2.values())).bounding_box()
        print(f"  bed 1: base {parts['base'].bounding_box().size.X:.0f} x {parts['base'].bounding_box().size.Y:.0f}; "
              f"bed 2: {len(bed2)} parts in {bb2.size.X:.0f} x {bb2.size.Y:.0f}")
