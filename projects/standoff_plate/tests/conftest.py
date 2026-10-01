import pytest

from projects.standoff_plate import params
from projects.standoff_plate.plate import build_hardware, build_plate


def pytest_generate_tests(metafunc):
    if "plate_name" in metafunc.fixturenames:
        metafunc.parametrize("plate_name", list(params.ACTIVE_PLATES), scope="session")


@pytest.fixture(scope="session")
def d(plate_name):
    return params.derive(plate_name)


@pytest.fixture(scope="session")
def plate(plate_name):
    return build_plate(plate_name)


@pytest.fixture(scope="session")
def hardware(plate_name):
    return build_hardware(plate_name)
