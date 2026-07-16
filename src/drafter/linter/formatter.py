"""LaTeXファイルの自動修正フォーマッタ CLI。"""

from __future__ import annotations
from pathlib import Path

import click

from drafter.formatter.pipeline import format_input_tree


@click.command()
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="起点となる LaTeX ファイル（main.tex 等）",
)
def main(input_path: Path) -> None:
    """LaTeX ファイル群を自動整形する。"""
    changed = format_input_tree(input_path)
    if changed:
        click.echo(f"format: updated {changed} file(s)")
    else:
        click.echo("format: OK")


if __name__ == "__main__":
    main()
