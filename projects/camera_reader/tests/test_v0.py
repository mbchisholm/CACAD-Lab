"""Camera reader V0: arithmetic (validate), every part builds as one valid
solid, the assembly's function checks, the bed, and overhang in each part's
declared print orientation (bridges named as exceptions)."""
import pytest
from build123d import Axis

from cacad.checks.overhang import check_overhang
from cacad.registries.materials import BED, NOZZLE
from projects.camera_reader import params
from projects.camera_reader.assembly import build_printed, check_assembly
from projects.camera_reader.hardware import build_hardware

SIZE = "V0"


@pytest.fixture(scope="session")
def printed():
    return build_printed(SIZE)


@pytest.fixture(scope="session")
def d():
    return params.validate(SIZE)


def test_validate_every_size():
    for s in params.SIZES:
        params.validate(s)


def test_parts_are_single_valid_solids(printed):
    for name, p in printed.items():
        assert p.is_valid and len(p.solids()) == 1, name


def test_assembly_function(printed):
    check_assembly(SIZE, printed, build_hardware(SIZE))


def _on_bed(name, p):
    """Rotate so the declared up is +Z."""
    up = params.PRINT_ORIENTATION[name]["up"]
    return {"+Z": p, "-Z": p.rotate(Axis.X, 180), "-Y": p.rotate(Axis.X, -90)}[up]


def test_fits_bed(printed):
    for name, p in printed.items():
        size = sorted(_on_bed(name, p).bounding_box().size)
        assert all(a <= b for a, b in zip(size, sorted(BED))), f"{name} {size}"


@pytest.mark.parametrize("name", ["snout", "cell_box", "retainer", "lid", "riser"])
def test_overhang(printed, d, name):
    p = _on_bed(name, printed[name])
    bed_z = p.bounding_box().min.Z
    exc = []
    if name == "cell_box":   # bridges: the snout opening's roof and the mask windows' roofs
        LZ = d["lens"][2]
        exc = [("snout opening", LZ + d["snout"]["far_in"][1] / 2), ("windows", LZ + d["window"][1] / 2)]
    check_overhang(p, dict(up=(0, 0, 1), bed_z=bed_z, max_deg=45.0, nozzle_d=NOZZLE, exceptions=exc))
