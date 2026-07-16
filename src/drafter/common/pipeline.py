"""Common pipeline placeholder."""

from __future__ import annotations

from pathlib import Path

import click


@click.command()
@click.option(
    "--input",
    "input_path",
    required=False,
    type=click.Path(path_type=Path),
    help="Optional input path (unused).",
)
def main(input_path: Path | None) -> None:
    _ = input_path
    click.echo("common: no pipeline to run")


if __name__ == "__main__":
    main()
