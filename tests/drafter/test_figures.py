"""Output names come from source files, not Task arguments."""

import subprocess
import base64
import zlib
from pathlib import Path
from unittest.mock import Mock
from urllib.parse import quote

import click
import pytest

from drafter import figures


@pytest.mark.parametrize("compressed", [False, True])
def test_drawio_global_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, compressed: bool
) -> None:
    directory = tmp_path / "figures/日本語の 図"
    directory.mkdir(parents=True)
    model = (
        '<mxGraphModel><root><object id="0" output="図.svg">'
        "<mxCell/></object></root></mxGraphModel>"
    )
    if compressed:
        compressor = zlib.compressobj(wbits=-15)
        data = compressor.compress(quote(model).encode()) + compressor.flush()
        content = base64.b64encode(data).decode()
    else:
        content = model
    source = directory / "source.drawio"
    source.write_text(f"<mxfile><diagram>{content}</diagram></mxfile>")
    command = Mock(return_value=Mock(returncode=0))
    monkeypatch.setattr(subprocess, "run", command)
    figures.render("drawio", source, tmp_path)
    args = command.call_args.args[0]
    assert args[args.index("--output") + 1] == str(directory / "図.svg")
    assert args[args.index("--page-index") + 1] == "0"
    assert "--svg-theme" in args


def test_mermaid_output_comment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory = tmp_path / "figures"
    directory.mkdir()
    source = directory / "flow.mmd"
    source.write_text("%% output: 日本語の 図.svg\nflowchart LR\n A --> B\n")
    command = Mock(return_value=Mock(returncode=0))
    monkeypatch.setattr(subprocess, "run", command)
    figures.render(None, source, tmp_path)
    assert command.call_args.args[0] == [
        "mmdc",
        "-i",
        str(source),
        "-o",
        str(directory / "日本語の 図.svg"),
    ]


def test_python_uses_script_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory = tmp_path / "figures"
    directory.mkdir()
    source = directory / "plot.py"
    source.touch()
    command = Mock(return_value=Mock(returncode=0))
    monkeypatch.setattr(subprocess, "run", command)
    figures.render("python", source, tmp_path)
    command.assert_called_once_with(
        ["uv", "run", "--script", str(source)], cwd=directory, check=False
    )


def test_output_must_stay_in_figures(tmp_path: Path) -> None:
    directory = tmp_path / "figures"
    directory.mkdir()
    source = directory / "flow.mmd"
    source.write_text("%% output: ../outside.svg\nflowchart LR\n A --> B\n")
    with pytest.raises(click.ClickException, match="under figures"):
        figures.render(None, source, tmp_path)


def test_plantuml_detects_type_and_uses_source_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = tmp_path / "figures"
    directory.mkdir()
    source = directory / "model.puml"
    source.write_text("' output: model.svg\n@startuml\nA -> B\n@enduml\n")
    command = Mock(return_value=Mock(returncode=0))
    monkeypatch.setattr(subprocess, "run", command)
    figures.render(None, source, tmp_path)
    assert command.call_args.args[0][:3] == ["plantuml", "-pipe", "-tsvg"]
    assert command.call_args.kwargs["input"] == source.read_bytes()
    assert (directory / "model.svg").is_file()


def test_missing_renderer_returns_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory = tmp_path / "figures"
    directory.mkdir()
    source = directory / "flow.mmd"
    source.write_text("%% output: flow.svg\nflowchart LR\nA --> B\n")
    command = Mock(side_effect=FileNotFoundError("mmdc"))
    monkeypatch.setattr(subprocess, "run", command)
    with pytest.raises(click.ClickException, match="mmdc"):
        figures.render(None, source, tmp_path)
