"""Unified host CLI; paper processing runs inside Compose."""

from __future__ import annotations

import os
import shlex
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import click
import yaml
from dotenv import load_dotenv

from drafter.converter.pipeline import run as convert
from drafter.converter.word_template_pipeline import run as generate_templates
from drafter.linter.pipeline import run as lint_paper
from drafter.workspace import create_paper, setup_workspace, validate_paper_name

REPO_ROOT = Path(__file__).resolve().parents[2]


def execute(args: list[str], env: dict[str, str] | None = None) -> None:
    try:
        result = subprocess.run(args, env=env, check=False)
    except OSError as exc:
        raise click.ClickException(str(exc)) from exc
    if result.returncode:
        raise click.exceptions.Exit(result.returncode)


def in_container(command: str, **options: str | Path | None) -> bool:
    if os.getenv("DRAFTER_IN_CONTAINER") == "1":
        return False
    args = [command]
    for name, value in options.items():
        if value is None:
            continue
        args.extend([f"--{name.replace('_', '-')}", str(value)])
    env = os.environ.copy()
    env.update(HOST_UID=str(os.getuid()), HOST_GID=str(os.getgid()))
    compose = shlex.split(os.getenv("DOCKER_COMPOSE", "docker compose"))
    forwarded = [
        "main_tex",
        "format",
        "skip_lint",
        "word_template",
        "word_template_dir",
        "DRAFTER_API_KEY",
        "DRAFTER_LLM_ENDPOINT",
        "DRAFTER_LLM_MODEL",
        "DRAFTER_LLM_MAX_CONTEXT_TOKENS",
    ]
    env_flags = [item for name in forwarded if name in env for item in ("-e", name)]
    previous = Path.cwd()
    try:
        os.chdir(REPO_ROOT)
        execute(
            [
                *compose,
                "run",
                "--rm",
                *env_flags,
                "drafter",
                "uv",
                "run",
                "drafter",
                *args,
            ],
            env,
        )
    finally:
        os.chdir(previous)
    return True


def settings(directory: Path) -> dict[str, str]:
    path = directory / "paper.yml"
    if not path.exists():
        return {}
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise click.ClickException(f"Cannot read {path}: {exc}") from exc
    if not isinstance(loaded, dict) or any(
        not isinstance(k, str) or not isinstance(v, str) for k, v in loaded.items()
    ):
        raise click.ClickException("paper.yml must be a mapping with string values.")
    return loaded


def choose(name: str, value: str | None, config: dict[str, str], default: str) -> str:
    return value if value is not None else os.getenv(name, config.get(name, default))


def input_file(value: str | None, config: dict[str, str]) -> Path:
    path = Path(choose("main_tex", value, config, "main.tex"))
    if not path.is_file():
        raise click.ClickException(f"Input file does not exist: {path}")
    return path


@contextmanager
def paper_directory(paper: str) -> Iterator[dict[str, str]]:
    validate_paper_name(paper)
    directory = REPO_ROOT / "papers" / paper
    if not directory.is_dir():
        raise click.ClickException(f"Paper directory does not exist: {directory}")
    config = settings(directory)
    previous = Path.cwd()
    try:
        os.chdir(directory)
        yield config
    finally:
        os.chdir(previous)


@click.group()
def main() -> None:
    """Create, check, review and compile papers. Docker is required for paper processing."""
    load_dotenv(REPO_ROOT / ".env", override=False, interpolate=False)


@main.command("compile")
@click.option("--paper", required=True, help="Paper directory name (Japanese/spaces supported).")
@click.option("--to", type=click.Choice(["pdf", "docx"]), default="pdf", show_default=True)
@click.option("--format", "layout", type=click.Choice(["article", "short", "review"]))
@click.option("--main-tex")
@click.option("--word-template")
@click.option("--word-template-dir", type=click.Path(path_type=Path))
@click.option("--skip-lint", type=click.Choice(["0", "1"]))
def compile_paper(
    paper: str,
    to: str,
    layout: str | None,
    main_tex: str | None,
    word_template: str | None,
    word_template_dir: Path | None,
    skip_lint: str | None,
) -> None:
    """Compile a paper to PDF or DOCX after linting."""
    validate_paper_name(paper)
    if in_container(
        "compile",
        paper=paper,
        to=to,
        format=layout,
        main_tex=main_tex,
        word_template=word_template,
        word_template_dir=word_template_dir,
        skip_lint=skip_lint,
    ):
        return
    with paper_directory(paper) as config:
        input_path = input_file(main_tex, config)
        skip = choose("skip_lint", skip_lint, config, "0")
        if skip not in {"0", "1"}:
            raise click.ClickException("skip_lint must be '0' or '1'.")
        if skip == "1":
            click.echo("lint: skipped explicitly (skip_lint=1)", err=True)
        elif lint_paper(input_path):
            raise click.exceptions.Exit(1)
        Path("dist").mkdir(exist_ok=True)
        if to == "pdf":
            env = os.environ.copy()
            env["BIBINPUTS"] = str(REPO_ROOT / "papers/bib") + os.pathsep
            execute(["latexmk", "-lualatex", "-output-directory=dist", str(input_path)], env)
            return
        layout = choose("format", layout, config, "article")
        if layout not in {"article", "short", "review"}:
            raise click.ClickException("format must be article, short or review.")
        template_dir = Path(
            choose(
                "word_template_dir",
                str(word_template_dir) if word_template_dir else None,
                config,
                str(REPO_ROOT / "templates/msword"),
            )
        )
        template = template_dir / choose(
            "word_template", word_template, config, f"template-{layout}.docx"
        )
        if not template.exists() and generate_templates(template_dir):
            raise click.exceptions.Exit(1)
        code = convert(
            input_path,
            tuple(sorted((REPO_ROOT / "papers/bib").glob("*.bib"))),
            template,
            REPO_ROOT / "templates/pandoc/defaults.yaml",
            Path("dist") / input_path.with_suffix(".docx").name,
            (Path.cwd(), REPO_ROOT / "figures"),
        )
        if code:
            raise click.exceptions.Exit(code)


@main.command("lint")
@click.option("--paper", required=True)
@click.option("--main-tex")
def lint(paper: str, main_tex: str | None) -> None:
    """Lint and format TeX (modifies input files)."""
    validate_paper_name(paper)
    if in_container("lint", paper=paper, main_tex=main_tex):
        return
    with paper_directory(paper) as config:
        code = lint_paper(input_file(main_tex, config))
        if code:
            raise click.exceptions.Exit(code)


@main.command("review")
@click.option("--paper", required=True)
@click.option("--main-tex")
def review(paper: str, main_tex: str | None) -> None:
    """Review a paper with the configured LLM."""
    validate_paper_name(paper)
    if in_container("review", paper=paper, main_tex=main_tex):
        return
    from drafter.reviewer.pipeline import run as review_paper

    with paper_directory(paper) as config:
        review_paper(
            input_file(main_tex, config),
            REPO_ROOT / "templates/rules",
            Path("dist/review-report.md"),
        )


@main.command("templates")
@click.option("--output-dir", type=click.Path(path_type=Path))
def templates(output_dir: Path | None) -> None:
    """Generate Word templates."""
    if in_container("templates", output_dir=output_dir):
        return
    code = generate_templates(output_dir or REPO_ROOT / "templates/msword")
    if code:
        raise click.exceptions.Exit(code)


@main.command("create-paper")
@click.option("--paper", required=True)
def create(paper: str) -> None:
    """Create a new paper skeleton without overwriting existing paths."""
    create_paper(Path(os.getenv("PAPERS_DIR", str(REPO_ROOT / "papers"))), paper)


@main.command("setup")
@click.option("--os", "target_os", required=True, type=click.Choice(["macos", "wsl"]))
def setup(target_os: str) -> None:
    """Check prerequisites and confirm workspace setup steps."""
    setup_workspace(REPO_ROOT, target_os)


@main.command("generate-figure")
@click.option("--mode", type=click.Choice(["drawio", "mermaid", "plantuml", "python"]))
@click.option("--path", required=True, type=click.Path(path_type=Path))
def generate_figure(mode: str | None, path: Path) -> None:
    """Generate a figure using the source's own output settings (runs on host)."""
    from drafter.figures import render

    render(mode, path, REPO_ROOT)
