"""cacad — build123d utilities, printability checks, FreeCAD cross-checks and
part registries shared by the projects in this repo.

Two assumptions run through everything: the build direction is Z, and a part
may be a Compound of several solids, so every probe and boolean works per
solid. Kernel facts the code encodes are in docs/FINDINGS.md. Requires
build123d 0.11.x. The thread helpers that used bd_warehouse are parked in
archive/cacad_threads.
"""
from build123d import Align

from .selectors import circular_edges, cylindrical_faces, line_edges_at_z, planar_faces_with_normal
from .finishing import try_chamfer
from .probes import (assert_bbox, assert_material, expect_solids, is_inside, max_overhang_deg, min_ring_wall,
                     min_section_wall, single_solid)
from .booleans import interference_pieces, interference_volume, volume_of
from .export import export, export_3mf, maybe_show

ALIGN_MIN_Z = (Align.CENTER, Align.CENTER, Align.MIN)

__all__ = [n for n in dir() if not n.startswith("_")]
