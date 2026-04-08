"""linter のエントリポイント。

使用方法:
    python -m drafter.linter.runner --input main.tex

exit code:
    0: 全チェック通過
    1: lintエラーあり
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from drafter.common.tex_parser import TexParser
from drafter.linter.rules import ALL_RULES, LintError


@click.command()
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="起点となる LaTeX ファイル（main.tex 等）",
)
def main(input_path: Path) -> None:
    """LaTeX ファイルの lint チェックを実行する。"""
    parser = TexParser()
    document = parser.parse(input_path)

    errors: list[LintError] = []
    for rule in ALL_RULES:
        errors.extend(rule(document))

    if errors:
        for err in errors:
            click.echo(err.format(), err=True)
        click.echo(f"\n{len(errors)} 件のエラーが見つかりました。", err=True)
        sys.exit(1)
    else:
        click.echo("lint: OK")


if __name__ == "__main__":
    main()
