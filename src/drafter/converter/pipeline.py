"""Converter pipeline entry point.

変換は2段構成。`from: latex+raw_tex` では Pandoc が `\\input{}` を展開せず
raw block として保持し、docx ライターがそれを捨ててしまうため、先に
`\\input{}` を解決した中間 .tex を書き出してから Pandoc に渡す。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click

from drafter.common.tex_parser import TexParser
from drafter.converter.config import build_expanded_tex_path, build_pandoc_command

#: resolve_inputs() が未検出ファイルの位置に埋め込むマーカー。
_MISSING_INPUT_MARKER = "[ERROR: file not found:"


def expand_inputs(input_path: Path, output: Path) -> Path:
    """`\\input{}` を再帰展開した中間 .tex を書き出してそのパスを返す。

    Args:
        input_path: 変換元の LaTeX ファイル（main.tex 等）。
        output: Pandoc の出力先。中間ファイルの置き場所の決定に使う。

    Returns:
        書き出した中間ファイルのパス。
    """
    expanded_path = build_expanded_tex_path(output)
    expanded = TexParser().resolve_inputs(input_path)
    expanded_path.write_text(expanded, encoding="utf-8")

    missing = expanded.count(_MISSING_INPUT_MARKER)
    if missing:
        click.echo(
            f"warning: {missing} \\input{{}} target(s) could not be resolved; see {expanded_path}",
            err=True,
        )
    return expanded_path


def run(
    input_path: Path,
    bibliography: tuple[Path, ...],
    template: Path | None,
    defaults: Path | None,
    output: Path,
    resource_path: tuple[Path, ...] = (),
) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    expanded_path = expand_inputs(input_path, output)
    click.echo(f"expand: {input_path} -> {expanded_path}")

    cmd = build_pandoc_command(
        input_path=expanded_path,
        output=output,
        bibliography=list(bibliography),
        template=template,
        defaults=defaults,
        resource_path=list(resource_path),
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
@click.option(
    "--resource-path",
    "resource_path",
    multiple=True,
    type=click.Path(path_type=Path),
    help="Directory to search for images (repeatable).",
)
def main(
    input_path: Path,
    bibliography: tuple[Path, ...],
    template: Path | None,
    defaults: Path | None,
    output: Path,
    resource_path: tuple[Path, ...],
) -> None:
    exit_code = run(
        input_path=input_path,
        bibliography=bibliography,
        template=template,
        defaults=defaults,
        output=output,
        resource_path=resource_path,
    )
    if exit_code != 0:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
