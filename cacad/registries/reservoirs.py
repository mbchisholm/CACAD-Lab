"""Reservoir registry: the few numbers an enclosure or lid insert touches.

A reservoir is modelled as an envelope plus the features a part mounts to,
not as a faithful tote. Every value is a caliper measurement on the actual
container; nobody publishes rim profiles. None means not measured yet.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Reservoir:
    name: str
    lid_outer: tuple | None       # (X, Y) lid outline at the rim, mm
    lid_thickness: float | None   # where a gland or bulkhead goes through, mm
    rim_lip: tuple | None         # (width, height) of the lip a bracket hooks over, mm
    wall_draft_deg: float | None  # side wall angle from vertical, for side mounts
    inner_depth: float | None     # lid underside to floor, mm
    fill_depth: float | None      # lid underside to working waterline, mm
    source: str = ""


# HDX 27 gal tote (the one on hand). Measure: lid outline, lid thickness at the
# flat, lip width and height, wall draft, depth, waterline at working fill.
HDX_27GAL = Reservoir(
    name="HDX_27GAL",
    lid_outer=None, lid_thickness=None, rim_lip=None,
    wall_draft_deg=None, inner_depth=None, fill_depth=None,
    source="not measured",
)

RESERVOIRS = {r.name: r for r in (HDX_27GAL,)}
