"""Chamfer with fallback sizes.

Assumes: `edges` all belong to `part`, and `part` is a single solid or a
compound whose solids do not overlap (OCC's chamfer walks the parent shape;
see FINDINGS F7 for why overlapping compounds are booleans' problem, and
chamfer the core solid *before* adding overlapping thread solids).
"""
from __future__ import annotations

import warnings
from typing import Iterable

from build123d import Edge, Part, chamfer


def try_chamfer(part: Part, edges: Iterable[Edge], size: float, fallbacks: Iterable[float],
                label: str, required: bool = False) -> Part:
    """Chamfer `edges` with `size`; on failure retry with each fallback in turn.

    Cosmetic use (default): returns the original part, with a warning, if
    every size fails, so a lead-in never blocks a build.
    Functional use (`required=True`): no fallbacks, raises on failure — for
    self-support chamfers and the like, where a smaller chamfer is a defect.
    Prints the size actually used so the log shows silent downgrades.
    """
    edges = list(edges)
    if required:
        assert edges, f"chamfer {label}: no edges selected"
        result = chamfer(edges, size)
        assert result.is_valid and len(result.solids()) == len(part.solids()), f"chamfer {label}: {size} failed"
        print(f"  chamfer {label}: {size} (required)")
        return result
    if not edges:
        warnings.warn(f"chamfer {label}: no edges selected, skipped", stacklevel=2)
        return part
    for s in (size, *fallbacks):
        try:
            result = chamfer(edges, s)
        except Exception as exc:  # OCC raises a variety of types
            print(f"  chamfer {label}: {s} failed ({type(exc).__name__}), trying smaller")
            continue
        if result.is_valid and len(result.solids()) == len(part.solids()):
            print(f"  chamfer {label}: {s}")
            return result
        print(f"  chamfer {label}: {s} produced invalid shape, trying smaller")
    warnings.warn(f"chamfer {label}: all sizes failed, left sharp", stacklevel=2)
    return part
