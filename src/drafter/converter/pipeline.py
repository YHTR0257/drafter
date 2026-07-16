"""Converter pipeline entry point."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click

from drafter.converter.config import build_pandoc_command


def run(
    input_path: Path,
    bibliography: tuple[Path, ...],
    template: Path | None,
    defaults: Path | None,
    output: Path,
) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_pandoc_command(
        input_path=input_path,
        output=output,
        bibliography=list(bibliography),
        template=template,
        defaults=defaults,
    )
    click.echo(f"run: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        click.echo(
            f"error: pandoc failed with exit code {result.returncode}.",
            err=True,
        )
        return result.returncode
    click.echo(f"output: {output}")
    return 0


@click.command()
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Input LaTeX file (main.tex, etc).",
)
@click.option(
    "--bibliography",
    "bibliography",
    multiple=True,
    type=click.Path(path_type=Path),
    help="Bib files to include (repeatable).",
)
@click.option(
    "--template",
    "template",
    default=None,
    type=click.Path(path_type=Path),
    help="Word template file.",
)
@click.option(
    "--defaults",
    "defaults",
    default=None,
    type=click.Path(path_type=Path),
    help="Pandoc defaults YAML file.",
)
@click.option(
    "--output",
    required=True,
    type=click.Path(path_type=Path),
    help="Output file path (.docx).",
)
def main(
    input_path: Path,
    bibliography: tuple[Path, ...],
    template: Path | None,
    defaults: Path | None,
    output: Path,
) -> None:
    exit_code = run(
        input_path=input_path,
        bibliography=bibliography,
        template=template,
        defaults=defaults,
        output=output,
    )
    if exit_code != 0:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
