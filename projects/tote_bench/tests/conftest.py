import pytest

from projects.tote_bench import params
from projects.tote_bench.bench import build_bench, check_bench


@pytest.fixture(scope="session")
def d():
    return params.validate()


@pytest.fixture(scope="session")
def parts():
    return build_bench()


@pytest.fixture(scope="session")
def checked(parts):
    """check_bench is the slow one (pairwise booleans, every screw): run it once per session."""
    return check_bench(parts)
