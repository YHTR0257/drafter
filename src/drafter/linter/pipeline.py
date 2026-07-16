"""Linter pipeline entry point."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from drafter.common.tex_parser import TexParser
from drafter.formatter.pipeline import format_input_tree
from drafter.linter.rules import ALL_RULES, LintError


def run(input_path: Path) -> int:
    changed = format_input_tree(input_path)
    if changed:
        click.echo(f"format: updated {changed} file(s)")
    else:
        click.echo("format: OK")

    parser = TexParser()
    document = parser.parse(input_path)

    errors: list[LintError] = []
    for rule in ALL_RULES:
        errors.extend(rule(document))

    if errors:
        for err in errors:
            click.echo(err.format(), err=True)
        click.echo(f"\n{len(errors)} errors found.", err=True)
        return 1

    click.echo("lint: OK")
    return 0


@click.command()
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Root LaTeX file (main.tex, etc).",
)
def main(input_path: Path) -> None:
    exit_code = run(input_path)
    if exit_code != 0:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
