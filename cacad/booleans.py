"""Boolean results and interference on parts that are compounds of overlapping
solids (FINDINGS F7, F13)."""
from __future__ import annotations

from build123d import Shape, ShapeList


def volume_of(x) -> float:
    """Volume of a boolean result, which may be None, a Shape or a ShapeList."""
    if x is None:
        return 0.0
    if isinstance(x, (list, tuple, ShapeList)):
        return sum(s.volume for s in x)
    return x.volume


def interference_volume(a: Shape, b: Shape) -> float:
    """Sum of pairwise solid-solid intersection volumes. Compound-vs-compound
    `intersect` is not a valid OCC argument when a compound's own solids
    overlap, and returns garbage without raising (F7). Overlap counted twice
    where two solids of `a` both cover the same region of `b`; use this as a
    zero/non-zero test or a same-tool comparison, not as an exact volume."""
    return sum(volume_of(sa.intersect(sb)) for sa in a.solids() for sb in b.solids())


def interference_pieces(a: Shape, b: Shape) -> list:
    """The pairwise intersection solids themselves, for locating an overlap."""
    out = []
    for sa in a.solids():
        for sb in b.solids():
            r = sa.intersect(sb)
            if r is None:
                continue
            out += [s for s in (r if isinstance(r, (list, tuple, ShapeList)) else [r]) if s.volume > 1e-6]
    return out
