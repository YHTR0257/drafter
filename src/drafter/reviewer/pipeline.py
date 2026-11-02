"""Reviewer pipeline entry point."""

from __future__ import annotations

from pathlib import Path

import click

from drafter.common.config import load_config
from drafter.common.tex_parser import TexParser
from drafter.reviewer.client import ReviewClient
from drafter.reviewer.prompt_builder import build_messages, load_rules
from drafter.reviewer.splitter import Chunk, Splitter


def run(input_path: Path, rules_dir: Path, output: Path) -> None:
    config = load_config()

    parser = TexParser()
    click.echo(f"parse: {input_path}")
    document = parser.parse(input_path)

    splitter = Splitter(
        max_tokens=config.llm.max_context_tokens,
        parser=parser,
    )
    chunks = splitter.split(document)
    click.echo(f"chunks: {len(chunks)}")

    client = ReviewClient(config.llm)
    results: list[tuple[Chunk, str]] = []

    for i, chunk in enumerate(chunks, 1):
        click.echo(f"[{i}/{len(chunks)}] review: {chunk.label}")
        rules = load_rules(rules_dir, chunk.label)
        messages = build_messages(chunk, rules)
        response = client.chat(messages)
        results.append((chunk, response))

    output.parent.mkdir(parents=True, exist_ok=True)
    _write_report(output, results)
    click.echo(f"output: {output}")


@click.command()
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Root LaTeX file (main.tex, etc).",
)
@click.option(
    "--rules-dir",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Directory containing YAML rules.",
)
@click.option(
    "--output",
    required=True,
    type=click.Path(path_type=Path),
    help="Review report output path.",
)
def main(input_path: Path, rules_dir: Path, output: Path) -> None:
    run(input_path=input_path, rules_dir=rules_dir, output=output)


def _write_report(output: Path, results: list[tuple[Chunk, str]]) -> None:
    lines: list[str] = ["# Review Report\n\n"]
    for chunk, response in results:
        lines.append(f"## {chunk.label}\n\n")
        lines.append(response.strip())
        lines.append("\n\n")
    output.write_text("".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
