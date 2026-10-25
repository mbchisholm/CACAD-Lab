"""The garage as a site: the quirks a build has to stand on, hug or clear.
Not a part. Each fact says where it came from; a rough number from the
owner is UNVERIFIED and the design that uses it carries an allowance for it.
Builds (projects/workbench, later projects/tote_rack) place themselves in
these coordinates and check against the solids garage.py makes.

Coordinates, one per wall that has been described (only the lip wall so far):
origin on the floor at the foot of the lip, at a station along the wall
the build chooses; +X along the wall, +Y out of the wall into the room,
+Z up. The wall face above the lip is y = 0; the lip's front face is
y = lip_depth; the floor at the lip's face is z = 0.

    section through the lip wall (looking along +X):

         wall |
              |   <- wall face, y = 0
              +------+  lip top, z = lip_h
              | LIP  |
              |      |  <- lip face, y = lip_depth
        ======+======+=================== floor, z = 0 (+- floor_dev further out)
"""
from __future__ import annotations

from types import MappingProxyType

IN = 25.4

WALLS = MappingProxyType(dict(
    lip_wall=MappingProxyType(dict(
        # Owner, 2026-10-07: "a concrete structure ... sticks out roughly 2.5 inches off the wall and then from there
        # down to the floor is about 6 inches. That lip goes the whole way along that wall." Rough; no photo yet.
        lip_depth=2.5 * IN,           # UNVERIFIED: wall face to lip face, owner's rough figure
        lip_h=6.0 * IN,               # UNVERIFIED: floor to lip top, owner's rough figure
        lip_h_dev=0.5 * IN,           # DESIGN allowance: "about 6" may be 5.5 to 6.5, or vary along the wall
        lip_material="concrete",
        # Owner, 2026-10-08: the wall above the lip is drywall. Framing behind it is not described; wood studs are the
        # usual garage wall. A build that screws into it reads these and says how to find the studs.
        finish="drywall",
        drywall_t_max=5 / 8 * IN,     # UNVERIFIED: 1/2 in is the IRC R302.6 garage-side minimum, 5/8 Type X is common;
                                      # a wall screw is sized to bite enough through the thicker one
        stud_oc=16 * IN,              # UNVERIFIED: the usual stud spacing; a build screws at every stud a stud finder shows
        length=None,                  # not given: a build reports its own length and the owner checks it fits
        source="owner, chat 2026-10-07 (lip, rough figures, no photo) and 2026-10-08 (drywall)",
    )),
))

FLOOR = MappingProxyType(dict(
    # Owner, 2026-10-07: "the floor is not perfectly level". No reading given. 1/2 in either way under any foot is a
    # DESIGN allowance for an ordinary garage slab sloped toward the door; the build's leveling range must cover it.
    floor_dev=0.5 * IN,               # UNVERIFIED allowance: floor under a foot may be this far above or below z = 0
    source="owner, chat 2026-10-07: 'not perfectly level'; magnitude is a DESIGN allowance",
))

DISPLAY = MappingProxyType(dict(
    # Drawing only: how much wall and slab to show behind and under a build. Not facts about the garage.
    wall_t=4.5 * IN,                  # wall drawn this thick behind y = 0
    wall_h=60.0 * IN,                 # wall drawn this tall above the floor
    slab_t=4.0 * IN,                  # slab drawn this thick under z = 0
    margin_x=12.0 * IN,               # wall, lip and slab drawn this far past each end of the build
    room_y=36.0 * IN,                 # slab drawn this far out from the wall
))


def derive(x0: float, x1: float, wall: str = "lip_wall") -> dict:
    """Site solids along [x0, x1] of `wall`, as name -> (size xyz, min corner xyz), plus the facts. Drawing extents
    come from DISPLAY; the lip, its face and its top are the facts."""
    w, f, g = dict(WALLS[wall]), dict(FLOOR), dict(DISPLAY)
    a, b = x0 - g["margin_x"], x1 + g["margin_x"]
    L = b - a
    d = dict(wall=wall, **w, floor_dev=f["floor_dev"], floor_source=f["source"], x_lo=a, x_hi=b)
    d["boxes"] = {
        "SLAB": ((L, g["wall_t"] + g["room_y"], g["slab_t"]), (a, -g["wall_t"], -g["slab_t"])),
        "LIP": ((L, w["lip_depth"], w["lip_h"]), (a, 0.0, 0.0)),
        "WALL": ((L, g["wall_t"], g["wall_h"]), (a, -g["wall_t"], 0.0)),
    }
    return d


if __name__ == "__main__":
    for name, w in WALLS.items():
        print(f"{name}: lip {w['lip_depth'] / IN:g} in deep x {w['lip_h'] / IN:g} in tall "
              f"(+-{w['lip_h_dev'] / IN:g}), {w['lip_material']}, length {w['length'] or 'unknown'}; {w['source']}")
    print(f"floor: +-{FLOOR['floor_dev'] / IN:g} in under any foot; {FLOOR['source']}")
