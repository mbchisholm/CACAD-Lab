import pytest

from projects.nft_table import params
from projects.nft_table.table import build_table


@pytest.fixture(scope="session")
def d():
    return params.derive()


@pytest.fixture(scope="session")
def parts(d):
    return build_table(d)


@pytest.fixture(scope="session")
def report(d, parts):
    from projects.nft_table.table import check_table
    return check_table(d, parts)
