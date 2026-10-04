"""P1 channel saddle. Clamps a level HFS5-2040 rail top with two M5 x 12 into HNTAJ5 nuts and cradles a Growrilla 100x50 on its corner
ledges and side walls only (the floor profile is not published). Seat height graded per rail (F/M/B) from the slope.

Built in its print frame (bed at z = 0, up +Z) from params.derive(); every number is from params.

    .venv/bin/python projects/nft_table/p1_saddle.py     # checks, prints the orientation report, writes out/<variant>.3mf
"""
from __future__ import annotations

from projects.nft_table import build as B
from projects.nft_table import printcheck as PC
from projects.nft_table.params import derive, print_parts

VARIANTS = ("P1-F", "P1-M", "P1-B")


def build(d=None) -> dict:
    """variant -> solid in its print frame."""
    d = d or derive()
    pp = print_parts(d)
    return {n: B.desc_solid(pp[n][0]) for n in VARIANTS}


def check(d=None) -> dict:
    """variant -> (solid, orientation report); raises on any print-check failure."""
    return PC.build_and_check(list(VARIANTS), d)


result = build()[VARIANTS[0]]   # the build123d-mcp sandbox shows `result`

if __name__ == "__main__":
    from cacad import export, export_3mf
    OUT = __file__.rsplit("/", 1)[0] + "/out"   # a string: the MCP sandbox rejects os/pathlib/sys anywhere in this file (F23)
    d = derive()
    qty = print_parts(d)
    for name, (solid, rep) in check(d).items():
        print(PC.orientation_report(rep) + f"\n  quantity {qty[name][1]}")
        export_3mf({name: solid}, OUT + f"/{name}.3mf")
        export(solid, name, OUT)
