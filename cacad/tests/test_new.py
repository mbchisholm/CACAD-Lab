import importlib.util

import pytest

from cacad.new import scaffold


def load(path):
    spec = importlib.util.spec_from_file_location("scaffolded_params", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_printed_scaffold_has_the_contract_files(tmp_path):
    files = {f.relative_to(tmp_path / "widget").as_posix() for f in scaffold("widget", root=tmp_path)}
    assert files == {"README.md", "params.py", "widget.py", "tests/conftest.py", "tests/test_widget.py"}
    for f in (tmp_path / "widget").rglob("*.py"):
        compile(f.read_text(), str(f), "exec")
    params = load(tmp_path / "widget" / "params.py")
    assert params.STATUS == "concept"
    params.validate("S1")


def test_bought_scaffold(tmp_path):
    files = {f.relative_to(tmp_path / "shelf").as_posix() for f in scaffold("shelf", bought=True, root=tmp_path)}
    assert files == {"README.md", "params.py", "tests/test_params.py"}
    load(tmp_path / "shelf" / "params.py").validate()


def test_refuses_bad_names_and_existing_projects(tmp_path):
    with pytest.raises(ValueError):
        scaffold("Bad-Name", root=tmp_path)
    scaffold("widget", root=tmp_path)
    with pytest.raises(FileExistsError):
        scaffold("widget", root=tmp_path)


def test_no_placeholder_left_unfilled(tmp_path):
    for f in scaffold("widget", root=tmp_path):
        assert "$name" not in f.read_text(), f
