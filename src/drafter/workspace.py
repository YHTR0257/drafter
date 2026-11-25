"""Host-side paper creation and interactive setup."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import click
from dotenv import dotenv_values, set_key

SECTIONS = ("introduction", "method", "result", "discussion", "conclusion")
PAPER_HEADER = r"""\documentclass{jlreq}
\usepackage{luatexja-fontspec}
\setmainfont[Path=/usr/share/fonts/ms-fonts/]{times.ttf}
\setmainjfont[Path=/usr/share/fonts/ms-fonts/,FontIndex=0]{msmincho.ttc}
\title{Title}
\author{}
\begin{document}
\maketitle
"""


def validate_paper_name(paper: str) -> None:
    if paper in {"", ".", ".."} or any(c in paper for c in "/\\\n\r\0"):
        raise click.BadParameter("Use a single directory name (Japanese and spaces are supported).")


def create_paper(papers_dir: Path, paper: str) -> None:
    validate_paper_name(paper)
    if not papers_dir.is_dir():
        raise click.ClickException(f"Paper parent directory does not exist: {papers_dir}")
    destination = papers_dir / paper
    try:
        destination.mkdir()  # Reject existing files, directories and symlinks atomically.
    except OSError as exc:
        raise click.ClickException(str(exc)) from exc
    (destination / "sections").mkdir()
    inputs = "".join(f"\\input{{sections/{section}}}\n" for section in SECTIONS)
    (destination / "main.tex").write_text(
        PAPER_HEADER + inputs + "\\end{document}\n", encoding="utf-8"
    )
    for section in SECTIONS:
        (destination / "sections" / f"{section}.tex").write_text(
            f"\\section{{{section.capitalize()}}}\n", encoding="utf-8"
        )
    (destination / ".latexmkrc").write_text(
        "$pdf_mode = 4;\n"
        "$lualatex = 'lualatex -synctex=1 -interaction=nonstopmode -halt-on-error %O %S';\n",
        encoding="utf-8",
    )
    (destination / "paper.yml").write_text(
        "main_tex: main.tex\nformat: article\n", encoding="utf-8"
    )
    click.echo(f"Created: {destination}")


def run_setup_command(args: list[str], root: Path) -> None:
    try:
        subprocess.run(args, cwd=root, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise click.ClickException(str(exc)) from exc


def setup_path(value: str, target_os: str) -> Path:
    if target_os == "wsl" and (re.match(r"^[A-Za-z]:[\\/]", value) or value.startswith("\\\\")):
        try:
            value = subprocess.check_output(["wslpath", "-u", value], text=True).strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            raise click.ClickException(f"Cannot convert Windows path with wslpath: {exc}") from exc
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise click.ClickException("Enter an absolute path.")
    if not path.exists():
        click.confirm(f"Create directory {path}?", abort=True)
        path.mkdir(parents=True)
    if not path.is_dir():
        raise click.ClickException(f"Not a directory: {path}")
    return path.resolve()


def setup_workspace(root: Path, target_os: str) -> None:
    for tool in ("docker", "git", "uv"):
        if shutil.which(tool) is None:
            raise click.ClickException(f"Install {tool} first (see README.md).")
    run_setup_command(["docker", "compose", "version"], root)
    run_setup_command(["docker", "info"], root)
    if shutil.which("task") is None:
        if target_os == "macos":
            if shutil.which("brew") is None:
                raise click.ClickException("Install Homebrew first (see README.md).")
            click.confirm("Install go-task with brew install go-task?", abort=True)
            run_setup_command(["brew", "install", "go-task"], root)
        else:
            click.confirm("Install go-task using https://taskfile.dev/install.sh?", abort=True)
            if shutil.which("curl") is None:
                raise click.ClickException("Install curl first.")
            with tempfile.TemporaryDirectory(prefix="drafter-task-") as temporary:
                installer = Path(temporary) / "install.sh"
                run_setup_command(
                    [
                        "curl",
                        "--proto",
                        "=https",
                        "--tlsv1.2",
                        "-LsSf",
                        "https://taskfile.dev/install.sh",
                        "-o",
                        str(installer),
                    ],
                    root,
                )
                target = Path.home() / ".local/bin"
                target.mkdir(parents=True, exist_ok=True)
                run_setup_command(["sh", str(installer), "-d", "-b", str(target)], root)
                os.environ["PATH"] = str(target) + os.pathsep + os.environ.get("PATH", "")
    if shutil.which("prek") is None:
        if not click.confirm("Install prek with uv tool install prek?", default=False):
            raise click.ClickException("prek is required for host development setup.")
        run_setup_command(["uv", "tool", "install", "prek"], root)
        tool_dir = subprocess.check_output(["uv", "tool", "dir", "--bin"], text=True).strip()
        os.environ["PATH"] = tool_dir + os.pathsep + os.environ.get("PATH", "")
    env_file = root / ".env"
    existing = env_file.exists()
    configure = not existing or click.confirm("Update the paths in existing .env?", default=False)
    if not configure:
        click.echo("Keeping existing .env.")
    else:
        if target_os == "wsl":
            click.echo(
                r"Windows paths such as C:\Users\name\papers are accepted (converted by wslpath)."
            )
        defaults = dotenv_values(env_file, interpolate=False) if existing else {}
        values: dict[str, str] = {}
        for key in ("PAPERS_DIR", "BIB_DIR", "FONTS_DIR"):
            value = click.prompt(key, default=defaults.get(key) or None, type=str)
            values[key] = str(setup_path(value, target_os))
        if not existing:
            with env_file.open("x", encoding="utf-8"):
                pass
        for key, value in values.items():
            set_key(env_file, key, value, quote_mode="always")
        os.environ.update(values)
    if click.confirm("Run uv sync --locked?", default=False):
        run_setup_command(["uv", "sync", "--locked"], root)
    if click.confirm("Install Git hooks with prek install?", default=False):
        run_setup_command(["prek", "install"], root)
    if click.confirm("Build the Docker image now (task docker:build)?", default=False):
        run_setup_command(["task", "docker:build"], root)
    click.echo("Setup steps finished. Run task help for commands.")
