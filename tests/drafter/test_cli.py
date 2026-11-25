"""Unified CLI settings, host dispatch, creation and setup."""

import shutil
import subprocess
import os
from pathlib import Path
from unittest.mock import Mock

import pytest
from click.testing import CliRunner
from dotenv import dotenv_values

from drafter import cli, workspace


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(cli, "REPO_ROOT", tmp_path)
    for name in [
        "PAPERS_DIR",
        "main_tex",
        "format",
        "skip_lint",
        "word_template",
        "word_template_dir",
    ]:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DRAFTER_IN_CONTAINER", "1")
    (tmp_path / "papers").mkdir()
    return tmp_path


def test_japanese_creation_preserves_existing(repo: Path) -> None:
    runner = CliRunner()
    args = ["create-paper", "--paper", "日本語の 論文"]
    assert runner.invoke(cli.main, args).exit_code == 0
    paper = repo / "papers/日本語の 論文"
    assert len(list((paper / "sections").glob("*.tex"))) == 5
    assert (paper / "paper.yml").is_file() and (paper / ".latexmkrc").is_file()
    original = (paper / "main.tex").read_bytes()
    assert runner.invoke(cli.main, args).exit_code != 0
    assert (paper / "main.tex").read_bytes() == original


@pytest.mark.parametrize("name", ["..", "../outside", "a/b", "a\\b", "bad\nname"])
def test_invalid_names(repo: Path, name: str) -> None:
    assert CliRunner().invoke(cli.main, ["create-paper", "--paper", name]).exit_code != 0
    assert not list((repo / "papers").iterdir())


def test_host_dispatch(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DRAFTER_IN_CONTAINER")
    monkeypatch.setenv("DRAFTER_API_KEY", "test-secret")
    command = Mock()
    monkeypatch.setattr(cli, "execute", command)
    result = CliRunner().invoke(cli.main, ["compile", "--paper", "論文 名", "--to", "pdf"])
    assert result.exit_code == 0, result.output
    args, env = command.call_args.args
    assert args[-6:] == ["drafter", "compile", "--paper", "論文 名", "--to", "pdf"]
    assert "DRAFTER_API_KEY" in args and "test-secret" not in args
    assert env["HOST_UID"] == str(os.getuid())


def test_paper_defaults_and_cli_priority(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paper = repo / "papers/sample"
    paper.mkdir()
    for name in ["原稿.tex", "override.tex"]:
        (paper / name).write_text("content")
    templates = repo / "templates"
    templates.mkdir()
    for name in ["custom.docx", "cli.docx"]:
        (templates / name).touch()
    (paper / "paper.yml").write_text(
        f"main_tex: 原稿.tex\nword_template: custom.docx\nword_template_dir: {templates}\n"
    )
    monkeypatch.setattr(cli, "lint_paper", Mock(return_value=0))
    convert = Mock(return_value=0)
    monkeypatch.setattr(cli, "convert", convert)
    runner = CliRunner()
    args = ["compile", "--paper", "sample", "--to", "docx"]
    result = runner.invoke(cli.main, args)
    assert result.exit_code == 0, result.output
    assert convert.call_args.args[0] == Path("原稿.tex")
    assert convert.call_args.args[2] == templates / "custom.docx"
    monkeypatch.setenv("main_tex", "override.tex")
    result = runner.invoke(
        cli.main, args + ["--main-tex", "原稿.tex", "--word-template", "cli.docx"]
    )
    assert result.exit_code == 0, result.output
    assert convert.call_args.args[0] == Path("原稿.tex")
    assert convert.call_args.args[2] == templates / "cli.docx"


def test_lint_blocks_compile(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paper = repo / "papers/sample"
    paper.mkdir()
    (paper / "main.tex").write_text("content")
    monkeypatch.setattr(cli, "lint_paper", Mock(return_value=1))
    command = Mock()
    monkeypatch.setattr(cli, "execute", command)
    runner = CliRunner()
    args = ["compile", "--paper", "sample"]
    assert runner.invoke(cli.main, args).exit_code == 1
    command.assert_not_called()
    result = runner.invoke(cli.main, args + ["--skip-lint", "1"])
    assert result.exit_code == 0, result.output
    assert command.call_args.args[0][0] == "latexmk"


@pytest.mark.parametrize("target", ["macos", "wsl"])
def test_setup_preserves_env(repo: Path, monkeypatch: pytest.MonkeyPatch, target: str) -> None:
    (repo / ".env").write_text("OTHER=value\n")
    monkeypatch.setattr(shutil, "which", lambda name: f"/bin/{name}")
    command = Mock()
    monkeypatch.setattr(workspace, "run_setup_command", command)
    result = CliRunner().invoke(cli.main, ["setup", "--os", target], input="n\nn\nn\nn\n")
    assert result.exit_code == 0, result.output
    assert (repo / ".env").read_text() == "OTHER=value\n"
    assert command.call_count == 2


def test_setup_updates_paths(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (repo / ".env").write_text("OTHER=value\n")
    monkeypatch.setattr(shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setattr(workspace, "run_setup_command", Mock())
    paths = [repo / "日本語の 論文", repo / "文献", repo / "fonts"]
    for path in paths:
        path.mkdir()
    answers = "y\n" + "\n".join(str(path) for path in paths) + "\nn\nn\nn\n"
    result = CliRunner().invoke(cli.main, ["setup", "--os", "macos"], input=answers)
    assert result.exit_code == 0, result.output
    values = dotenv_values(repo / ".env")
    assert values["OTHER"] == "value" and values["PAPERS_DIR"] == str(paths[0])


def test_windows_path_conversion(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = repo / "Windowsからの 論文"
    target.mkdir()
    command = Mock(return_value=f"{target}\n")
    monkeypatch.setattr(subprocess, "check_output", command)
    assert workspace.setup_path(r"C:\Users\name\論文", "wsl") == target
    command.assert_called_once_with(["wslpath", "-u", r"C:\Users\name\論文"], text=True)


@pytest.mark.parametrize("target", ["macos", "wsl"])
def test_setup_install_method(repo: Path, monkeypatch: pytest.MonkeyPatch, target: str) -> None:
    (repo / ".env").write_text("OTHER=value\n")
    monkeypatch.setattr(shutil, "which", lambda name: None if name == "task" else f"/bin/{name}")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: repo / "home"))
    monkeypatch.setenv("PATH", os.environ["PATH"])
    command = Mock()
    monkeypatch.setattr(workspace, "run_setup_command", command)
    result = CliRunner().invoke(cli.main, ["setup", "--os", target], input="y\nn\nn\nn\nn\n")
    assert result.exit_code == 0, result.output
    commands = [call.args[0] for call in command.call_args_list]
    if target == "macos":
        assert ["brew", "install", "go-task"] in commands
    else:
        assert any(
            args[0] == "curl" and "https://taskfile.dev/install.sh" in args for args in commands
        )
        assert any(args[0] == "sh" and "-b" in args for args in commands)
