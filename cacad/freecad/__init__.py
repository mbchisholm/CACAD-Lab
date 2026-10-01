"""FreeCAD as a second implementation, reached over the freecad-mcp addon's
XML-RPC server (127.0.0.1:9875, `execute_code`).

Three jobs FreeCAD has earned here: (1) re-derive placements and booleans
from the params dict and compare (`rederive`), (2) BOP-check every solid and
face of a part from STEP and from exact BREP (`shape_check`), (3) freeze a
KiCad board to STEP through KiCadStepUp (`kicad_freeze`). Composing
assemblies in FreeCAD was tried and dropped: the same collisions are caught
in build123d without the GUI, the 90 s dispatch budget, or a binary file.

FreeCAD 1.1.3 ships OpenCascade 7.8.1; build123d 0.11.1 runs 7.9.3. That is
a second implementation, not a second kernel.
"""
from .rpc import FreeCADRPC
from .rederive import PAIRWISE_COMMON, compare, pairwise_common_in_freecad
from .shape_check import CHECK_CODE, check_part, summarize

__all__ = ["FreeCADRPC", "PAIRWISE_COMMON", "compare", "pairwise_common_in_freecad",
           "CHECK_CODE", "check_part", "summarize"]
