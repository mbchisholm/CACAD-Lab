"""Minimum printable feature vs nozzle multiples."""
from __future__ import annotations

from cacad.probes import min_ring_wall, min_section_wall  # noqa: F401  (min_section_wall: the plate-style wall_probe)


def check_walls_vs_nozzle(walls: dict[str, float], params: dict) -> None:
    """params: nozzle_d, wall_multiple (default 2). `walls` is the analytic
    table name -> thickness. Every entry must be >= wall_multiple * nozzle_d."""
    lim = params.get("wall_multiple", 2.0) * params["nozzle_d"]
    for name, w in walls.items():
        assert w >= lim - 1e-9, f"wall {name} = {w:.2f} < {params.get('wall_multiple', 2.0)} x {params['nozzle_d']} nozzle"


def check_slots_vs_nozzle(slot_widths: dict[str, float], params: dict) -> None:
    """params: nozzle_d, slot_multiple (default 1)."""
    lim = params.get("slot_multiple", 1.0) * params["nozzle_d"]
    for name, w in slot_widths.items():
        assert w >= lim - 1e-9, f"slot {name} = {w:.2f} < {lim} (nozzle)"


def check_measured_walls(part, params: dict, wall_probe=min_ring_wall) -> dict[str, float]:
    """Cross-sections of the real solid, not the table. params: nozzle_d,
    wall_multiple, min_wall (optional functional floor), probes: {name: z}.
    `wall_probe(part, z)` is min_ring_wall for parts arranged around Z, or
    min_section_wall for plates and other off-axis parts. Returns the
    measured values for the report."""
    lim = max(params.get("wall_multiple", 2.0) * params["nozzle_d"], params.get("min_wall", 0.0))
    out = {}
    for name, z in params["probes"].items():
        out[name] = w = wall_probe(part, z)
        assert w >= lim - 1e-9, f"{name}: measured wall {w:.2f} < {lim}"
    return out
