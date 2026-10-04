"""bd_warehouse IsoThread handling that encodes kernel facts (FINDINGS F3, F5, F6).

Assumes: bd_warehouse 0.3.x `IsoThread` (a Compound of one solid per turn),
thread axis along Z with local z=0 at one end.
"""
from __future__ import annotations

from build123d import Compound, Part, Solid


def solid_thread(major: float, pitch: float, length: float, external: bool,
                 end_finishes: tuple[str, str], interference: float = 0.2) -> Solid:
    """An IsoThread pre-fused into ONE solid.

    The per-turn solids fuse cleanly among themselves. Fusing the raw
    multi-solid compound onto a body in one boolean can return an empty
    compound without raising (F3). Keep `interference` at the library default
    of 0.2 (F5) and prefer `with_threads` over fusing the result onto its
    core (F6).
    """
    from bd_warehouse.thread import IsoThread
    th = IsoThread(major_diameter=major, pitch=pitch, length=length, external=external,
                   end_finishes=end_finishes, interference=interference)
    turns = th.solids()
    one = turns[0].fuse(*turns[1:]) if len(turns) > 1 else turns[0]
    solids = one.solids()
    assert len(solids) == 1 and one.is_valid, "thread turns did not fuse into one solid"
    return solids[0]


def with_threads(core: Part, threads: list[Solid], label: str) -> Compound:
    """Assemble a finished core solid and its thread solids into one part
    without a boolean. The threads overlap the core by `interference`, so a
    slicer unions the shells; the kernel never sees a fuse seam (F6).
    Consequence: booleans against this part must be pairwise (F7)."""
    solids = core.solids()
    assert len(solids) == 1, "core must be a single solid before threads are added"
    part = Compound(children=[solids[0], *threads], label=label)
    assert part.is_valid, f"{label}: compound invalid"
    return part
