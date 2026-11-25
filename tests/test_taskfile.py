"""Exercise Task routing with a stub uv executable."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

TASK_BIN = os.environ.get("TASK_BIN") or shutil.which("task")
pytestmark = pytest.mark.skipif(not TASK_BIN, reason="go-task required (or set TASK_BIN)")
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("task", "options", "expected"),
    [
        (
            "compile:pdf",
            ["paper=日本語の 論文"],
            ["compile", "--paper", "日本語の 論文", "--to", "pdf"],
        ),
        (
            "compile:docx",
            ["paper=sample", "format=review"],
            ["compile", "--paper", "sample", "--to", "docx", "--format", "review"],
        ),
        ("lint", ["paper=sample"], ["lint", "--paper", "sample"]),
        ("review", ["paper=sample"], ["review", "--paper", "sample"]),
        ("create:paper", ["paper=新規論文"], ["create-paper", "--paper", "新規論文"]),
        ("setup", ["os=macos"], ["setup", "--os", "macos"]),
        ("setup", ["os=wsl"], ["setup", "--os", "wsl"]),
        ("generate:fig", ["path=figures/図.mmd"], ["generate-figure", "--path", "figures/図.mmd"]),
        (
            "generate:fig:plantuml",
            ["path=figures/図.puml"],
            ["generate-figure", "--path", "figures/図.puml", "--mode", "plantuml"],
        ),
    ],
)
def test_routes(tmp_path: Path, task: str, options: list[str], expected: list[str]) -> None:
    shutil.copy(ROOT / "Taskfile.yml", tmp_path)
    shutil.copytree(ROOT / "tools/go-task", tmp_path / "tools/go-task")
    stub = tmp_path / "uv"
    stub.write_text("#!/usr/bin/env python3\nimport json, sys\nprint(json.dumps(sys.argv[1:]))\n")
    stub.chmod(0o755)
    result = subprocess.run(
        [str(TASK_BIN), task, *options],
        cwd=tmp_path,
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == ["run", "drafter", *expected]


@pytest.mark.parametrize("args", [["compile:pdf"], ["setup"], ["setup", "os=windows"]])
def test_required_inputs(args: list[str]) -> None:
    result = subprocess.run([str(TASK_BIN), *args], cwd=ROOT, capture_output=True, timeout=30)
    assert result.returncode != 0


def test_help_without_configuration(tmp_path: Path) -> None:
    shutil.copy(ROOT / "Taskfile.yml", tmp_path)
    shutil.copytree(ROOT / "tools/go-task", tmp_path / "tools/go-task")
    for args in [[], ["help"], ["--list"]]:
        result = subprocess.run(
            [str(TASK_BIN), *args], cwd=tmp_path, text=True, capture_output=True, timeout=30
        )
        assert result.returncode == 0, result.stderr
        assert "compile:pdf" in result.stdout and "compile:docx" in result.stdout
