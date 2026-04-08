"""reviewer のエントリポイント。

使用方法:
    python -m drafter.reviewer.runner \\
        --input main.tex \\
        --rules-dir ../../templates/rules \\
        --output dist/review-report.md
"""

from __future__ import annotations

from pathlib import Path

import click

from drafter.common.config import load_config
from drafter.common.tex_parser import TexParser
from drafter.reviewer.client import ReviewClient
from drafter.reviewer.prompt_builder import build_messages, load_rules
from drafter.reviewer.splitter import Chunk, Splitter


@click.command()
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="起点となる LaTeX ファイル（main.tex 等）",
)
@click.option(
    "--rules-dir",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="ルール YAML ファイルが格納されたディレクトリ",
)
@click.option(
    "--output",
    required=True,
    type=click.Path(path_type=Path),
    help="レビューレポートの出力先（Markdown）",
)
def main(input_path: Path, rules_dir: Path, output: Path) -> None:
    """LLM を使って LaTeX 論文をレビューし、Markdown レポートを出力する。"""
    config = load_config()

    parser = TexParser()
    click.echo(f"パース中: {input_path}")
    document = parser.parse(input_path)

    splitter = Splitter(
        max_tokens=config.llm.max_context_tokens,
        parser=parser,
    )
    chunks = splitter.split(document)
    click.echo(f"チャンク数: {len(chunks)}")

    client = ReviewClient(config.llm)
    results: list[tuple[Chunk, str]] = []

    for i, chunk in enumerate(chunks, 1):
        click.echo(f"[{i}/{len(chunks)}] レビュー中: {chunk.label}")
        rules = load_rules(rules_dir, chunk.label)
        messages = build_messages(chunk, rules)
        response = client.chat(messages)
        results.append((chunk, response))

    output.parent.mkdir(parents=True, exist_ok=True)
    _write_report(output, results)
    click.echo(f"レポート出力: {output}")


def _write_report(output: Path, results: list[tuple[Chunk, str]]) -> None:
    """レビュー結果を Markdown ファイルに書き出す。"""
    lines: list[str] = ["# レビューレポート\n\n"]
    for chunk, response in results:
        lines.append(f"## {chunk.label}\n\n")
        lines.append(response.strip())
        lines.append("\n\n")
    output.write_text("".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
