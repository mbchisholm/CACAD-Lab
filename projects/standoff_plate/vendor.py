"""Vendor STEP models of the boards, placed where params.derive puts each
board, and checked against the registry and the plate:

- outline and thickness: the STEP's PCB solid against Board.size and the
  plate's board_t;
- holes: every registry hole has a STEP hole within `hole_tol`, and the screw
  passes the STEP's hole;
- fit: the placed model intersects neither the plate, the screws, the nuts,
  the mount screws, nor the other boards' models. A screw head on a component
  shows up here.

A board with no VENDOR_STEPS row, or whose STEP is not in this machine's
ref/ (gitignored), stands in as its registry envelope and is reported as one.

    .venv/bin/python projects/standoff_plate/vendor.py     # NUTRIENT_ANALOG -> out/*_boards.step, *_screws.step
"""
from __future__ import annotations

from build123d import Axis, Compound, GeomType, Location, import_step
from OCP.BRepAdaptor import BRepAdaptor_Surface

from cacad import interference_volume
from projects.standoff_plate.params import NUTRIENT_ANALOG, VENDOR_STEPS, _rot, derive
from projects.standoff_plate.plate import build_hardware, build_plate

PROJECT = __file__.rsplit("/", 1)[0]   # a string: no os/pathlib in a part file (F23)
OUTLINE_TOL = 0.05     # STEP PCB outline vs Board.size, mm
THICKNESS_TOL = 0.02   # STEP PCB thickness vs the plate's board_t, mm
HOLE_TOL = 0.05        # STEP hole axis vs registry hole, mm


def _pcb(c: Compound):
    """The PCB: the thin solid (< 2 mm) with the largest plan area."""
    thin = [s for s in c.solids() if s.bounding_box().size.Z < 2.0]
    return max(thin, key=lambda s: s.bounding_box().size.X * s.bounding_box().size.Y)


def load_model(name: str) -> dict | None:
    """The vendor model in the registry board frame (outline centre at x = y = 0, PCB underside at z = 0), with
    the facts read off it. None when the board has no vendor STEP on this machine."""
    row = VENDOR_STEPS.get(name)
    if row is None:
        return None
    try:
        raw = import_step(f"{PROJECT}/{row['path']}")
    except (OSError, ValueError, RuntimeError):
        return None
    pb = _pcb(raw).bounding_box()
    cx, cy = (pb.min.X + pb.max.X) / 2, (pb.min.Y + pb.max.Y) / 2
    holes = set()
    for f in _pcb(raw).faces().filter_by(GeomType.CYLINDER):   # through holes: Z-axis cylinders inside the outline
        cyl = BRepAdaptor_Surface(f.wrapped).Cylinder()
        p, r = cyl.Axis().Location(), cyl.Radius()
        if abs(cyl.Axis().Direction().Z()) > 0.99 and 0.9 < r < 2.0 \
                and pb.min.X + 0.5 < p.X() < pb.max.X - 0.5 and pb.min.Y + 0.5 < p.Y() < pb.max.Y - 0.5:
            hx, hy = _rot((p.X() - cx, p.Y() - cy), row["rot"])
            holes.add((round(hx, 3), round(hy, 3), round(2 * r, 3)))
    size = (pb.size.X, pb.size.Y) if row["rot"] % 180 == 0 else (pb.size.Y, pb.size.X)
    model = raw.moved(Location((-cx, -cy, -pb.min.Z))).rotate(Axis.Z, row["rot"])
    return dict(model=model, size=size, thickness=pb.size.Z, holes=sorted(holes), source=row["source"])


def place_models(plate: str) -> dict:
    """Each board of the plate: its vendor model (or None) placed on its bosses."""
    d = derive(plate)
    out = []
    for pb in d["boards"]:
        m = load_model(pb["name"])
        placed = None
        if m is not None:
            placed = m["model"].rotate(Axis.Z, pb["rot"]).moved(Location((*pb["xy"], d["z_board_bottom"])))
        out.append(dict(board=pb, vendor=m, placed=placed))
    return dict(d=d, boards=out)


def check_vendor(plate: str, part=None, hw=None) -> dict:
    """Registry and fit checks for every vendor model on the plate. Raises; returns what it measured."""
    pm = place_models(plate)
    d = pm["d"]
    part = part if part is not None else build_plate(plate)
    hw = hw if hw is not None else build_hardware(plate)
    rep = []
    for i, e in enumerate(pm["boards"]):
        b, m, label = e["board"]["board"], e["vendor"], f"{plate}: {e['board']['name']} #{i}"
        if m is None:
            rep.append(dict(board=b.name, vendor=None))
            continue
        for k in (0, 1):
            assert abs(m["size"][k] - b.size[k]) <= OUTLINE_TOL, f"{label}: STEP outline {m['size']} vs registry {b.size}"
        assert abs(m["thickness"] - d["board_t"]) <= THICKNESS_TOL, f"{label}: STEP PCB {m['thickness']:.3f} vs board_t {d['board_t']}"
        for hx, hy in b.holes:
            near = [h for h in m["holes"] if abs(h[0] - hx) <= HOLE_TOL and abs(h[1] - hy) <= HOLE_TOL]
            assert near, f"{label}: registry hole ({hx}, {hy}) not in the STEP (holes {m['holes']})"
            assert d["screw_spec"]["d"] < near[0][2], f"{label}: {d['screw']} does not pass the STEP's {near[0][2]} hole"
        fit = {k: interference_volume(e["placed"], hw[k]) for k in ("screws", "nuts", "mount_screws") if hw[k].solids()}
        fit["plate"] = interference_volume(e["placed"], part)
        for j, o in enumerate(pm["boards"]):
            if j > i and o["placed"] is not None:
                fit[f"board #{j}"] = interference_volume(e["placed"], o["placed"])
        bad = {k: v for k, v in fit.items() if v > 1e-6}
        assert not bad, f"{label}: vendor model intersects " + ", ".join(f"{k} by {v:.4f} mm^3" for k, v in bad.items())
        rep.append(dict(board=b.name, vendor=m["source"], step_holes=m["holes"], thickness=m["thickness"], fit=fit))
    return dict(boards=rep, placed=pm["boards"])


def boards_compound(plate: str, placed: list, hw: dict) -> Compound:
    """Vendor models where there are any, registry envelopes for the rest: what the FreeCAD view shows."""
    envelopes = hw["boards"].solids()
    return Compound(children=[e["placed"] if e["placed"] is not None else envelopes[i] for i, e in enumerate(placed)])


if __name__ == "__main__":
    from cacad import export
    OUT = PROJECT + "/out"
    for plate in NUTRIENT_ANALOG:
        part, hw = build_plate(plate), build_hardware(plate)
        r = check_vendor(plate, part, hw)
        for b in r["boards"]:
            print(f"{plate}: {b['board']}: " + (f"vendor STEP ({b['vendor']}), PCB {b['thickness']:.2f}, holes ok, fit "
                                                 + ", ".join(f"{k} {v:.4f}" for k, v in b["fit"].items())
                                                 if b["vendor"] else "no vendor STEP: registry envelope"))
        export(part, f"standoff_plate_{plate}", OUT)
        export(boards_compound(plate, r["placed"], hw), f"standoff_plate_{plate}_boards", OUT)
        export(Compound(children=[*hw["screws"].solids(), *hw["nuts"].solids()]), f"standoff_plate_{plate}_screws", OUT)
