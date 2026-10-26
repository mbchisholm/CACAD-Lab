import pytest

from projects.module_grid import params
from projects.module_grid.base import build_base
from projects.module_grid.clamp import build_jaw, build_tile


def pytest_generate_tests(metafunc):
    if "base_name" in metafunc.fixturenames:
        metafunc.parametrize("base_name", list(params.ACTIVE_BASES), scope="session")
    if "clamp_name" in metafunc.fixturenames:
        metafunc.parametrize("clamp_name", list(params.ACTIVE_CLAMPS), scope="session")


@pytest.fixture(scope="session")
def base(base_name):
    return build_base(base_name)


@pytest.fixture(scope="session")
def clamp_parts(clamp_name):
    return build_tile(clamp_name), build_jaw(clamp_name)
