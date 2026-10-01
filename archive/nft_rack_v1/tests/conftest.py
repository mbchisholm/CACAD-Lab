import pytest

from projects.nft_rack import params
from projects.nft_rack.rack import build_rack


def pytest_generate_tests(metafunc):
    if "rack_name" in metafunc.fixturenames:
        metafunc.parametrize("rack_name", list(params.ACTIVE_RACKS), scope="session")


@pytest.fixture(scope="session")
def d(rack_name):
    return params.derive(rack_name)


@pytest.fixture(scope="session")
def parts(rack_name):
    return build_rack(rack_name)
