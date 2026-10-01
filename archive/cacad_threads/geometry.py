"""Small closed-form geometry used when deriving parameters."""
from __future__ import annotations

import math


def iso_core_radius(major: float, pitch: float) -> float:
    """Root radius of a bd_warehouse IsoThread (same for internal and external).

    IsoThread.min_radius = major/2 - 5/8 * H, H = sqrt(3)/2 * pitch. A core
    cylinder must use exactly this radius (FINDINGS F5, knife-edge note).
    """
    h = math.sqrt(3) / 2 * pitch
    return major / 2 - 5 / 8 * h


def hex_across_corners(af: float) -> float:
    """Across-corners of a hexagon from across-flats."""
    return af / math.cos(math.radians(30))


def clamp_force_n(torque_nm: float, major_mm: float, k: float) -> float:
    """Bolt clamp force from torque, F = T / (k d)."""
    return torque_nm / (k * major_mm / 1000)
