import pytest

from projects.tote_bench import params
from projects.tote_bench.bench import build_bench


def pytest_generate_tests(metafunc):
    if "version" in metafunc.fixturenames:
        metafunc.parametrize("version", list(params.ACTIVE_VERSIONS), scope="session")


@pytest.fixture(scope="session")
def d(version):
    return params.derive(version)


@pytest.fixture(scope="session")
def parts(version):
    return build_bench(version)
