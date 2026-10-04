"""A file's syntax tree is parsed once per content, however many bounds resolve into it."""

import ast
from pathlib import Path

from epure import bound


def test_a_file_is_parsed_once_per_content(tmp_path: Path, monkeypatch):
    src = tmp_path / "m.py"
    src.write_text("def f():\n    return 1\n\ndef g():\n    return 2\n", encoding="utf-8")
    parses = []
    real = ast.parse
    monkeypatch.setattr(ast, "parse", lambda *a, **k: parses.append(1) or real(*a, **k))
    assert bound.resolve("m.py::f", tmp_path).name == "f"
    assert bound.resolve("m.py::g", tmp_path).name == "g"
    assert len(parses) == 1
    src.write_text("def f():\n    return 3\n", encoding="utf-8")
    assert bound.resolve("m.py::f", tmp_path).name == "f"
    assert len(parses) == 2, "a changed file is parsed again"
