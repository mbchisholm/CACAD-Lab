"""Scaffold a project from docs/templates/.

    .venv/bin/python -m cacad.new <name>            # printed part: params, part file, tests
    .venv/bin/python -m cacad.new <name> --bought   # bought-and-cut: params and tests only

The new project passes its own tests on creation. Fill in `params.py`, then
the README sections. `--root` writes somewhere other than `projects/`.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from string import Template

REPO = Path(__file__).resolve().parents[1]
TEMPLATES = REPO / "docs" / "templates"
NAME = re.compile(r"^[a-z][a-z0-9_]*$")
RENAME = {"part.py": "{name}.py", "tests/test_part.py": "tests/test_{name}.py"}


def scaffold(name: str, bought: bool = False, root: Path | None = None) -> list[Path]:
    if not NAME.match(name):
        raise ValueError(f"project name {name!r}: lowercase letters, digits and underscores, starting with a letter")
    root = Path(root) if root else REPO / "projects"
    dest = root / name
    if dest.exists():
        raise FileExistsError(f"{dest} already exists")
    kind = TEMPLATES / ("bought" if bought else "printed")
    written = []
    for src in sorted(kind.rglob("*.tmpl")):
        rel = src.relative_to(kind).as_posix().removesuffix(".tmpl")
        rel = RENAME.get(rel, rel).format(name=name)
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(Template(src.read_text()).substitute(name=name))
        written.append(out)
    return written


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name")
    ap.add_argument("--bought", action="store_true", help="bought-and-cut project, no printed geometry")
    ap.add_argument("--root", help="directory to create the project in (default: projects/)")
    a = ap.parse_args(argv)
    try:
        files = scaffold(a.name, a.bought, a.root)
    except (ValueError, FileExistsError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    for f in files:
        print(f"created {f.relative_to(Path(a.root).parent) if a.root else f.relative_to(REPO)}")
    print(f"next: edit projects/{a.name}/params.py, run its tests, then fill in the README")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
