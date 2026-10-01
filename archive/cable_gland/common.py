"""Gland-local glue. Every generic helper lives in `cacad`; only what reads
this project's params dict or its output folder stays here."""
from __future__ import annotations

from pathlib import Path

from build123d import Shape
import cacad

OUT_DIR = Path(__file__).parent / "out"


def export(part: Shape, name: str, out_dir: Path = OUT_DIR) -> tuple[Path, Path]:
    return cacad.export(part, name, out_dir)


def assert_walls(d: dict):
    for name, w in d["walls"].items():
        assert w >= d["min_wall"], f"wall {name} = {w:.2f} < {d['min_wall']}"
