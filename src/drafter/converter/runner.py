"""converter のエントリポイント。

使用方法:
    python -m drafter.converter.runner \\
        --input main.tex \\
        --bibliography ../../bib/foo.bib \\
        --template ../../templates/msword/manuscript.docx \\
        --defaults ../../templates/pandoc/defaults.yaml \\
        --output dist/main.docx
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click

from drafter.converter.config import build_pandoc_command


@click.command()
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="変換元の LaTeX ファイル（main.tex 等）",
)
@click.option(
    "--bibliography",
    "bibliography",
    multiple=True,
    type=click.Path(path_type=Path),
    help="参照する .bib ファイル（複数指定可）",
)
@click.option(
    "--template",
    "template",
    default=None,
    type=click.Path(path_type=Path),
    help="Word テンプレートファイル（--reference-doc に渡す）",
)
@click.option(
    "--defaults",
    "defaults",
    default=None,
    type=click.Path(path_type=Path),
    help="Pandoc defaults YAML ファイル",
)
@click.option(
    "--output",
    required=True,
    type=click.Path(path_type=Path),
    help="出力先ファイル（.docx 等）",
)
def main(
    input_path: Path,
    bibliography: tuple[Path, ...],
    template: Path | None,
    defaults: Path | None,
    output: Path,
) -> None:
    """Pandoc を使って LaTeX を DOCX に変換する。"""
    output.parent.mkdir(parents=True, exist_ok=True)

    cmd = build_pandoc_command(
        input_path=input_path,
        output=output,
        bibliography=list(bibliography),
        template=template,
        defaults=defaults,
    )

    click.echo(f"実行: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        click.echo(f"エラー: pandoc が終了コード {result.returncode} で失敗しました。", err=True)
        sys.exit(result.returncode)

    click.echo(f"変換完了: {output}")


if __name__ == "__main__":
    main()
