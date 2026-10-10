import pytest

from projects.seedling_wheel import params
from projects.seedling_wheel.p1_hub import build_part as p1
from projects.seedling_wheel.p2_pivot import build_part as p2
from projects.seedling_wheel.p3_hanger import build_part as p3
from projects.seedling_wheel.p4_corner import build_part as p4
from projects.seedling_wheel.p5_head import build_part as p5

BUILDERS = {"p1_hub": p1, "p2_pivot": p2, "p3_hanger": p3, "p4_corner": p4, "p5_head": p5}


@pytest.fixture(scope="session")
def d():
    return params.derive(params.ACTIVE_SIZES[0])


@pytest.fixture(scope="session", params=list(BUILDERS))
def built(request):
    return request.param, BUILDERS[request.param](params.ACTIVE_SIZES[0])
