"""Three layers per plate: geometry + function (check_plate), manufacturability
(walls measured on the section, declared orientation, overhang with the nut
pocket ceilings as the only declared exceptions), and the arithmetic of every
inactive plate."""
import pytest

from projects.standoff_plate import params
from projects.standoff_plate.plate import check_plate
from cacad import min_section_wall
from cacad.checks.orientation import check_declared_orientation
from cacad.checks.overhang import check_overhang
from cacad.checks.printability import check_measured_walls, check_walls_vs_nozzle


def test_geometry_and_function(plate_name, plate):
    check_plate(plate_name, plate)


def test_every_plate_validates_or_fails_for_a_stated_reason():
    """Inactive plates still run the arithmetic: a failure must name a missing fact or a missing feature."""
    for name in params.PLATES:
        try:
            params.validate(name)
        except AssertionError as e:
            assert name not in params.ACTIVE_PLATES, f"active plate fails validate(): {e}"
            assert any(k in str(e) for k in ("unknown", "not designed", "plug needs")), f"{name}: unexpected failure: {e}"


def test_walls_table_vs_nozzle(d):
    check_walls_vs_nozzle(d["walls"], dict(nozzle_d=d["nozzle_d"]))


def test_walls_measured_on_sections(d, plate):
    got = check_measured_walls(plate, dict(
        nozzle_d=d["nozzle_d"], min_wall=d["min_wall"],
        probes={"pocket level": d["pocket_depth"] / 2,
                "web level": d["pocket_depth"] + d["pocket_web"] / 2,
                "boss level": d["plate_t"] + d["standoff_h"] / 2}), wall_probe=min_section_wall)
    assert abs(got["boss level"] - d["boss_wall"]) < 0.02, got
    assert abs(got["pocket level"] - d["walls"]["plate edge (pocket corner to plate edge)"]) < 0.02, got


def test_declared_orientation(d, plate):
    check_declared_orientation(plate, d["print_orientation"]["plate"])


def test_overhang_only_at_declared_nut_pocket_ceilings(d, plate):
    o = d["print_orientation"]["plate"]
    rep = check_overhang(plate, dict(up=o["up"], bed_z=o["bed_z"], max_deg=d["max_overhang_deg"],
                                     nozzle_d=d["nozzle_d"], exceptions=o["overhang_exceptions"]))
    assert len(rep["exceptions_found"]) == len(d["holes"]), rep   # one ceiling per pocket, no more
    # every declared ceiling is a bridge no wider than the pocket across corners
    assert all(area < 3.2 * d["pocket_r"] ** 2 for _, _, area, _ in rep["exceptions_found"]), rep


def test_screw_stack(d, hardware):
    """Stock screw reaches through the nut and stops above the bed face."""
    sc = d["screw_spec"]
    bb = hardware["screws"].bounding_box()
    assert bb.min.Z == pytest.approx(d["screw_tip_z"], abs=1e-6)
    assert d["screw_tip_z"] >= d["screw_tip_min"]
    assert d["screw_tip_z"] <= d["pocket_depth"] - sc["nut_m"] + 1e-9
    assert bb.max.Z == pytest.approx(d["z_head_top"], abs=1e-6)
