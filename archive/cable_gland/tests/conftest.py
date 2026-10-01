import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import params  # noqa: E402
from body import build_body  # noqa: E402
from collet import build_collet  # noqa: E402
from insert import build_insert  # noqa: E402
from nut import build_nut  # noqa: E402


def pytest_generate_tests(metafunc):
    if "size" in metafunc.fixturenames:
        metafunc.parametrize("size", list(params.ACTIVE_SIZES), scope="session")


@pytest.fixture(scope="session")
def d(size):
    return params.derive(size)


@pytest.fixture(scope="session")
def body(size):
    return build_body(size)


@pytest.fixture(scope="session")
def collet(size):
    return build_collet(size)


@pytest.fixture(scope="session")
def nut(size):
    return build_nut(size)


@pytest.fixture(scope="session")
def inserts(size, d):
    return {i: build_insert(size, i) for i in d["insert_ids"]}
