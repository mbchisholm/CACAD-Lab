"""Lumber-project helpers shared by the wood-frame projects (raised_bed, tote_rack):
a cut plan against stocked lengths and the closest approach of two screw axes.

Both take plain numbers (mm) and tuples; no build123d here, so params.py files
can import them without the kernel.
"""
from __future__ import annotations

import math


def cut_plan(pieces: list[tuple[str, float]], stock: float, end_trim: float, kerf: float) -> list[list[tuple[str, float]]]:
    """First-fit decreasing: pack pieces into sticks of `stock`, each losing `end_trim` at one end and a kerf per cut.
    Returns one list of (name, length) per stick."""
    usable = stock - end_trim
    sticks: list[list[tuple[str, float]]] = []
    for name, ln in sorted(pieces, key=lambda p: -p[1]):
        assert ln + kerf <= usable + 1e-9, f"piece {name} {ln:.1f} longer than usable stock {usable:.1f}"
        for st in sticks:
            if sum(l + kerf for _, l in st) + ln + kerf <= usable + 1e-9:
                st.append((name, ln))
                break
        else:
            sticks.append([(name, ln)])
    return sticks


def seg_dist(p0, p1, q0, q1) -> float:
    """Closest distance between segments p0-p1 and q0-q1 in 3D (Ericson, Real-Time Collision Detection 5.1.9)."""
    d1 = [b - a for a, b in zip(p0, p1)]
    d2 = [b - a for a, b in zip(q0, q1)]
    r = [a - b for a, b in zip(p0, q0)]
    a = sum(x * x for x in d1)
    e = sum(x * x for x in d2)
    f = sum(x * y for x, y in zip(d2, r))
    eps = 1e-12
    if a <= eps and e <= eps:
        return math.dist(p0, q0)
    if a <= eps:
        s, t = 0.0, min(max(f / e, 0.0), 1.0)
    else:
        c = sum(x * y for x, y in zip(d1, r))
        if e <= eps:
            t, s = 0.0, min(max(-c / a, 0.0), 1.0)
        else:
            b = sum(x * y for x, y in zip(d1, d2))
            denom = a * e - b * b
            s = min(max((b * f - c * e) / denom, 0.0), 1.0) if denom != 0.0 else 0.0
            t = (b * s + f) / e
            if t < 0.0:
                t, s = 0.0, min(max(-c / a, 0.0), 1.0)
            elif t > 1.0:
                t, s = 1.0, min(max((b - c) / a, 0.0), 1.0)
    c1 = [p + s * d for p, d in zip(p0, d1)]
    c2 = [q + t * d for q, d in zip(q0, d2)]
    return math.dist(c1, c2)
