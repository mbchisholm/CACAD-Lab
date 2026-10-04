"""STEP, STL and 3MF export, and optional ocp-vscode display."""
from __future__ import annotations

import warnings

from build123d import Mesher, Shape, export_step, export_stl

# `sys` and `pathlib` are imported inside the functions: the build123d-mcp sandbox
# blocks them, and these functions only run from a script's __main__.


def export(part: Shape, name: str, out_dir: Path) -> tuple[Path, Path]:
    """Write <out_dir>/<name>.step and .stl. A compound of overlapping solids
    exports as multiple shells; slicers union them (FINDINGS F5b)."""
    from pathlib import Path
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    step, stl = out_dir / f"{name}.step", out_dir / f"{name}.stl"
    export_step(part, str(step))
    export_stl(part, str(stl))
    return step, stl


def export_3mf(parts: dict[str, Shape], path: Path) -> Path:
    """Write one named mesh object per part, whatever its solid count.

    `Mesher.add_shape` flattens a Compound into one 3MF object per child, so
    an unfused core+thread part arrives in the slicer as separate objects and
    the 0.2 mm thread interference (F5b) becomes an object collision instead
    of a union (FINDINGS F15). Tessellate the whole part into one mesh instead.
    """
    from pathlib import Path
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    m = Mesher()
    for name, part in parts.items():
        if part.is_null:   # property in 0.11.1, like is_valid (F1)
            raise ValueError(f"{name}: empty shape, nothing to mesh")
        verts, tris = Mesher._mesh_shape(part, 0.001, 0.1)
        if len(verts) < 3 or not tris:
            raise ValueError(f"{name}: degenerate shape, nothing to mesh")
        mesh = m.model.AddMeshObject()
        mesh.SetGeometry(*Mesher._create_3mf_mesh(verts, tris))
        mesh.SetName(name)
        mesh.SetPartNumber(name)
        if not mesh.IsValid():
            raise RuntimeError(f"{name}: 3mf mesh is invalid")
        if not mesh.IsManifoldAndOriented():
            warnings.warn(f"{name}: 3mf mesh is not manifold", stacklevel=2)
        m.model.AddBuildItem(mesh, m.wrapper.GetIdentityTransform())
    m.write(str(path))
    return path


def maybe_show(*objs, names=None, flag: str = "--show"):
    """Show in ocp-vscode only if `flag` is on the command line and the viewer
    answers, so scripts stay headless by default."""
    import sys
    if flag not in sys.argv:
        return
    try:
        from ocp_vscode import show
        show(*objs, names=names)
    except Exception as exc:
        print(f"ocp_vscode show skipped: {exc}", file=sys.stderr)
