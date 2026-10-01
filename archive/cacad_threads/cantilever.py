"""Cantilever root strain vs a material allowable with a layer-orientation factor."""
from __future__ import annotations


def cantilever_root_strain(tip_deflection: float, thickness: float, length: float) -> float:
    """Tip-loaded cantilever, root bending strain: 3 * delta * t / (2 * L^2).
    First-order; ignores taper along the finger."""
    return 3 * tip_deflection * thickness / (2 * length**2)


def check_cantilever(finger: dict, params: dict) -> dict:
    """finger: length, root_thickness, tip_deflection.
    params: material (key), materials {name: bulk allowable strain},
    layer_factor (bulk -> across-layer estimate when the root bends across
    layer lines; 1.0 if the part prints with the finger in-plane),
    govern ('across' or 'bulk'): which allowable the assertion uses.
    Always reports both, so a margin is never read against the wrong one."""
    eps = cantilever_root_strain(finger["tip_deflection"], finger["root_thickness"], finger["length"])
    bulk = params["materials"][params["material"]]
    across = bulk * params.get("layer_factor", 1.0)
    limit = across if params.get("govern", "across") == "across" else bulk
    rep = dict(root_strain=eps, bulk_allowable=bulk, across_layer_allowable=across, governing=params.get("govern", "across"),
               deflection_to_thickness=finger["tip_deflection"] / finger["root_thickness"])
    assert eps <= limit + 1e-9, (f"root strain {eps:.2%} > {params['material']} allowable {limit:.2%} "
                                  f"({rep['governing']}; bulk {bulk:.1%}, across layers {across:.1%})")
    return rep
