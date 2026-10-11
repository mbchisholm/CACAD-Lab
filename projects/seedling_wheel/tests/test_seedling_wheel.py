"""Three layers: the arithmetic (validate), each printed part (geometry, walls, declared orientation, overhang), and
the assembly through the turn (an analytic sweep every degree, solid overlaps at four angles, designed contacts)."""
import math

import pytest
from build123d import Location

from cacad.checks.orientation import check_declared_orientation
from cacad.checks.overhang import check_overhang
from cacad.checks.printability import check_walls_vs_nozzle
from projects.seedling_wheel import params
from projects.seedling_wheel.assembly import assemble, check_assembly, interferences
from projects.seedling_wheel.p1_hub import check_part as c1
from projects.seedling_wheel.p2_pivot import check_part as c2
from projects.seedling_wheel.p3_hanger import check_part as c3
from projects.seedling_wheel.p4_corner import check_part as c4
from projects.seedling_wheel.p5_head import check_part as c5
from projects.seedling_wheel.p7_hanger import check_part as c7
from projects.seedling_wheel.p8_nacelle import check_part as c8
from projects.seedling_wheel.p10_shoe import check_part as c10

CHECKS = {"p1_hub": c1, "p2_pivot": c2, "p3_hanger": c3, "p4_corner": c4, "p5_head": c5, "p7_hanger": c7,
          "p8_nacelle": c8, "p10_shoe": c10}


def test_every_size_validates():
    for size in params.SIZES:
        params.validate(size)


def test_geometry_and_function(built):
    name, part = built
    CHECKS[name](params.ACTIVE_SIZES[0], part)


def test_walls_vs_nozzle(d):
    check_walls_vs_nozzle(d["walls"], dict(nozzle_d=d["nozzle_d"]))


def test_declared_orientation(d, built):
    name, part = built
    check_declared_orientation(part, d["print_orientation"][name])


def test_no_undeclared_overhang(d, built):
    name, part = built
    o = d["print_orientation"][name]
    check_overhang(part, dict(up=o["up"], bed_z=o["bed_z"], max_deg=d["max_overhang_deg"],
                              nozzle_d=d["nozzle_d"], exceptions=o["overhang_exceptions"]))


def test_fits_the_bed(built):
    from cacad.registries.materials import BED
    _, part = built
    s = part.bounding_box().size
    assert max(s.X, s.Y) <= BED[0] and s.Z <= BED[2]


def test_tray_drops_in_free(d):
    """The tray sits on the rails with tray_clear to every P4 fence: located, never pressed."""
    parts = assemble(0.0)
    for k in ("+1+1", "+1-1", "-1+1", "-1-1"):
        gap = parts["A tray"][1].distance_to(parts[f"A P4 {k}"][1])
        assert abs(gap - d["c"]["tray_clear"]) < 1e-3, f"P4 {k}: tray gap {gap:.3f}"


def test_sweep_every_degree(d):
    """The two gondola envelopes (W x H boxes hung from pivots 2R apart) keep sweep_gap at every angle, and the
    sweep stays between the base and the light. Independent of the closed form in validate()."""
    w, top, bot, R = d["w_gondola"], d["env_top"], d["env_bot"], d["R"]
    least = math.inf
    for k in range(360):
        p = math.radians(k)
        dy, dz = 2 * R * math.sin(p), 2 * R * math.cos(p)
        gy = abs(dy) - w                      # > 0: separated in Y
        gz = abs(dz) - (top - bot)            # > 0: separated in Z
        sep = math.hypot(max(gy, 0), max(gz, 0)) if (gy > 0 or gz > 0) else -1
        least = min(least, sep)
        for sg in (1, -1):
            zp = d["z_axis"] + sg * R * math.cos(p)
            assert zp + bot >= d["ext"]["a"] + d["c"]["ground_gap"] - 1e-6, f"{k} deg: hits the base"
            assert zp + top <= d["z_light"] - d["c"]["light_gap"] + 1e-6, f"{k} deg: hits the light"
    assert least >= d["c"]["sweep_gap"] - 1e-6, f"least gondola clearance {least:.1f}"


@pytest.mark.parametrize("phi", [0.0, 45.0, 90.0, 135.0])
def test_no_overlaps_through_the_turn(phi):
    check_assembly(phi)


def test_overlap_check_catches_a_1mm_shift():
    parts = assemble(0.0)
    moved = {k: (g, Location((1.0, 0, 0)) * s if g == "A" else s) for k, (g, s) in parts.items()}
    assert interferences(moved), "negative control: shifting gondola A 1 mm into its pivot stack must overlap"


def test_designed_contacts_touch():
    parts = assemble(30.0)
    touch = [("A P3 +1", "A post +1"), ("P2 A+1", "arm +1"), ("P1 +1", "arm +1"), ("Pololu hub +1", "P1 +1"),
             ("shoulder screw A+1", "P2 A+1"), ("washer A+1.0", "A P3 +1"), ("A post +1", "A crossbar +1"),
             ("A tray", "A rail +1"), ("gearmotor +1", "P5 +1"), ("T5 bar 0", "P7 +1"),
             ("A P4 +1+1", "A crossbar +1"), ("A P4 -1-1", "A crossbar -1"), ("P5 +1", "mast +1"),
             ("P5 +1", "leg +1+1"), ("P5 -1", "leg -1-1"), ("leg +1+1", "foot +1"), ("mast +1", "ridge"),
             ("P8 +1", "mast +1"), ("P8 +1", "leg +1-1"), ("P8 -1", "leg -1+1"), ("spine", "foot -1"),
             ("P7 -1", "ridge"), ("P7 +1", "ridge"), ("T5 bar 2", "P7 -1"), ("P10 +1+1", "leg +1+1"),
             ("P10 +1-1", "foot +1"), ("P10 -1+1", "leg -1+1"), ("P10 -1-1", "foot -1"), ("P9 pod", "foot -1")]
    for a, b in touch:
        assert parts[a][1].distance_to(parts[b][1]) < 1e-3, f"{a} does not touch {b}"
    gap = parts["washer A+1.1"][1].distance_to(parts["P2 A+1"][1])
    assert abs(gap - params.derive()["c"]["sh_play"]) < 1e-3, "pivot stack play"
