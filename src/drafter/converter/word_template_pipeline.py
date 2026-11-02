"""Word テンプレート生成 pipeline entry point。

`templates/msword/` は gitignore 対象のため、テンプレート docx 自体は
リポジトリに含めない。クローン直後はこの pipeline で再生成する。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click

from drafter.converter.word_template import ALL_SPECS, build_template

DEFAULT_OUTPUT_DIR = Path("templates/msword")


def load_base_docx() -> bytes:
    """Pandoc 既定の reference.docx をベーステンプレートとして取得する。

    Returns:
        docx のバイト列。

    Raises:
        RuntimeError: pandoc の起動に失敗した場合。
    """
    try:
        result = subprocess.run(
            ["pandoc", "--print-default-data-file", "reference.docx"],
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("pandoc not found. install pandoc first.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"pandoc failed: {exc.stderr.decode(errors='replace')}") from exc
    return result.stdout


def run(output_dir: Path) -> int:
    try:
        base_docx = load_base_docx()
    except RuntimeError as exc:
        click.echo(f"error: {exc}", err=True)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    for spec in ALL_SPECS:
        output = output_dir / spec.filename
        output.write_bytes(build_template(base_docx, spec))
        click.echo(f"output: {output} ({spec.label})")
    return 0


@click.command()
@click.option(
    "--output-dir",
    "output_dir",
    default=DEFAULT_OUTPUT_DIR,
    show_default=True,
    type=click.Path(file_okay=False, path_type=Path),
    help="Directory to write the generated Word templates into.",
)
def main(output_dir: Path) -> None:
    exit_code = run(output_dir)
    if exit_code != 0:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
