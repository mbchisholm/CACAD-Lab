import pytest

from projects.workbench import params
from projects.workbench.bench import build_bench


def pytest_generate_tests(metafunc):
    if "bench_name" in metafunc.fixturenames:
        metafunc.parametrize("bench_name", list(params.ACTIVE_BENCHES), scope="session")


@pytest.fixture(scope="session")
def d(bench_name):
    return params.derive(bench_name)


@pytest.fixture(scope="session")
def parts(bench_name):
    return build_bench(bench_name)
