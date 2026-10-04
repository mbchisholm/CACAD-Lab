"""Build every active size, run its checks, export STEP + STL to out/.

    python build.py            # all ACTIVE_SIZES
    python build.py M16        # one size
"""
from __future__ import annotations

import sys
import time

import params
from assembly import assemble
from body import build_body, check_body
from collet import build_collet, check_collet
from common import OUT_DIR, export
from insert import build_insert, check_insert, insert_name
from nut import build_nut, check_nut


def build_size(size: str) -> None:
    t = time.time()
    d = params.validate(size)
    body, collet, nut = build_body(size), build_collet(size), build_nut(size)
    check_body(body, size)
    check_collet(collet, size)
    check_nut(nut, size)
    for name, part in (("body", body), ("collet", collet), ("nut", nut)):
        export(part, f"{name}_{size}")
    inserts = {}
    for i in d["insert_ids"]:
        ins = build_insert(size, i)
        check_insert(ins, size, i)
        export(ins, insert_name(size, i))
        inserts[i] = ins
    asm = assemble(size, dict(body=body, collet=collet, nut=nut, insert=inserts[d["insert_ids"][0]]))
    export(asm, f"gland_{size}_assembly")
    print(f"{size}: built + checked in {time.time() - t:.1f}s -> {OUT_DIR}/  "
          f"(inserts: {', '.join(f'ID{i:.1f}' for i in d['insert_ids'])})")


if __name__ == "__main__":
    requested = [a for a in sys.argv[1:] if a in params.SIZES]
    for size in requested or params.ACTIVE_SIZES:
        build_size(size)
