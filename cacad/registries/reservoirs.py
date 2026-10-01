"""Reservoir registry: the vendor-published envelope of a tote plus the
DESIGN fields a plumbing layout needs.

Nobody publishes rim profiles, lid thickness or wall draft. A part that
mounts to a tote is designed to tolerate them (a lid range, a rough-cut
window under a printed plate), not to depend on them. No field gates on a
measurement.
"""
from dataclasses import dataclass

IN = 25.4


@dataclass(frozen=True)
class Reservoir:
    name: str
    model: str
    exterior_top: tuple       # (L, W, H) mm, vendor: outside at the top of the tote, H overall
    interior_bottom: tuple    # (L, W, H) mm, vendor: inside at the bottom, H inside depth
    capacity_l: float         # vendor nominal capacity, litres
    lid_t_range: tuple        # DESIGN (min, max) lid thickness a lid-mounted part must accept, mm
    fill_depth: float         # DESIGN working waterline above the inside floor, mm
    freeboard: float          # DESIGN least air between the waterline and the lid underside at drain-back, mm
    source: str = ""


HDX_27GAL = Reservoir(
    name="HDX_27GAL",
    model="HDX 27 gal Tough Storage Tote, model 999-27G-HDX (Home Depot Internet 327528802, store SKU 207585)",
    exterior_top=(28.6 * IN, 19.6 * IN, 15.2 * IN),
    interior_bottom=(22.98 * IN, 14.02 * IN, 14.30 * IN),
    capacity_l=27 * 3.785411784,
    lid_t_range=(1.5, 5.0),
    fill_depth=8.0 * IN,
    freeboard=25.0,
    source=("homedepot.com 999-27G-HDX product page, wayback 2026-03-08 (projects/nft_table/ref/vendor_sheets/"
            "pp_grommets_tote_pump/homedepot_HDX27_999-27G-HDX_wayback20260308.html): 'Exterior (at top of tote) "
            "28.6 in L x 19.6 in W x 15.2 in H', 'Interior (at bottom of tote) 22.98 in L x 14.02 in W x 14.30 in H'. "
            "The spec table's 28.5 in depth disagrees with 28.6; 28.6 used. The 2025 page under SKU 207585 was a "
            "different tote (Strong Box). lid_t_range, fill_depth, freeboard: DESIGN"),
)

RESERVOIRS = {r.name: r for r in (HDX_27GAL,)}
