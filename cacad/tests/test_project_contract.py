"""Every project follows the same shape, and nothing private or heavy is
tracked. Scaffold a project with `python -m cacad.new <name>` and this passes.

LEGACY_README lists projects whose README predates the template (sections
Status, Sources, Run; under 80 lines). The list only shrinks."""
import importlib
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PROJECTS = sorted(p for p in (REPO / "projects").iterdir() if p.is_dir() and (p / "params.py").exists())
STATUSES = ("concept", "passes", "printed", "parked")
README_SECTIONS = ("## Status", "## Sources", "## Run")
README_MAX_LINES = 80
LEGACY_README = {"camera_reader", "nft_table", "raised_bed",
                 "standoff_plate", "tote_rack"}

PRIVATE = [re.compile(p) for p in (r"/Users/[A-Za-z]", "T1" + "TRTA", r"\bvault\b")]
PRIVATE_OK = {".mcp.json"}   # absolute PYTHONPATH; see issue #16
BINARY_EXT = {".fcstd", ".step", ".stp", ".stl", ".3mf", ".pdf", ".zip", ".brd", ".kicad_pcb"}
MAX_BYTES = 1_000_000


def tracked():
    try:
        out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")
    return [REPO / f for f in out.splitlines()]


@pytest.mark.parametrize("project", PROJECTS, ids=lambda p: p.name)
def test_project_shape(project):
    assert (project / "README.md").exists(), "README.md"
    assert any((project / "tests").glob("test_*.py")), "tests/test_*.py"
    status = importlib.import_module(f"projects.{project.name}.params").STATUS
    assert status in STATUSES, f"STATUS {status!r} not in {STATUSES}"


@pytest.mark.parametrize("project", PROJECTS, ids=lambda p: p.name)
def test_readme_follows_template(project):
    if project.name in LEGACY_README:
        pytest.skip("legacy README; remove from LEGACY_README when rewritten")
    lines = (project / "README.md").read_text().splitlines()
    missing = [s for s in README_SECTIONS if s not in lines]
    assert not missing, f"README missing sections {missing}"
    assert len(lines) <= README_MAX_LINES, f"README is {len(lines)} lines; long-form goes in NOTES.md or SPEC.md"


def test_no_private_references():
    hits = []
    for f in tracked():
        if f.name in PRIVATE_OK or f.suffix.lower() in (".png", ".jpg", ".lock") or not f.is_file():
            continue
        try:
            text = f.read_text()
        except UnicodeDecodeError:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if "/Users/..." in line:
                continue
            if any(p.search(line) for p in PRIVATE):
                hits.append(f"{f.relative_to(REPO)}:{n}: {line.strip()[:80]}")
    assert not hits, "private path or name in a tracked file:\n" + "\n".join(hits)


def test_no_binaries_or_big_files():
    bad = [f"{f.relative_to(REPO)}" for f in tracked()
           if f.is_file() and (f.suffix.lower() in BINARY_EXT or f.stat().st_size > MAX_BYTES)]
    assert not bad, f"generated or heavy files tracked (belong in out/ or ref/): {bad}"
