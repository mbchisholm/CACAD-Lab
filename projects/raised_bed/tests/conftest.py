import pytest

from projects.raised_bed import params
from projects.raised_bed.bed import build_bed


def pytest_generate_tests(metafunc):
    if "bed_name" in metafunc.fixturenames:
        metafunc.parametrize("bed_name", list(params.ACTIVE_BEDS), scope="session")


@pytest.fixture(scope="session")
def d(bed_name):
    return params.derive(bed_name)


@pytest.fixture(scope="session")
def parts(bed_name):
    return build_bed(bed_name)
