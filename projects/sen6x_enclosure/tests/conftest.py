import pytest

from projects.sen6x_enclosure import enclosure


@pytest.fixture(scope="session")
def built():
    """base, lid, hardware, keepouts. Needs ref/SEN6x.step (gitignored): the Sensirion STEP PS_CD_SEN6x_D1."""
    from pathlib import Path
    assert Path(enclosure.SENSOR_STEP).exists(), (
        f"{enclosure.SENSOR_STEP} missing: copy Sensirion's PS_CD_SEN6x_D1.STEP there (see README)")
    return enclosure.build_all()
