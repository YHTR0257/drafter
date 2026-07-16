"""Common LaTeX formatting pipeline."""

from __future__ import annotations

import re
from pathlib import Path

import click

# Collapse 3+ consecutive blank lines into 2.
_MULTI_BLANK_RE = re.compile(r"\n{3,}")

# Normalize Japanese comma to ASCII comma.
_JAPANESE_COMMA_RE = re.compile("、")

# Normalize compatibility CJK radicals to common kanji.
_COMPAT_KANJI_MAP: dict[str, str] = {
    "⼦": "子",
    "⼒": "力",
    "⾜": "足",
    "⽐": "比",
    "⽬": "目",
}
_COMPAT_KANJI_RE = re.compile("|".join(map(re.escape, _COMPAT_KANJI_MAP)))


def format_file(path: Path) -> bool:
    """Format a .tex file and return True when it changed."""
    original = path.read_text(encoding="utf-8")
    result = _apply_formatting(original)
    if result == original:
        return False
    path.write_text(result, encoding="utf-8")
    return True


def format_input_tree(root_path: Path) -> int:
    r"""Format the root file and its \input{} tree, returning change count."""
    changed = 0
    for tex_path in _collect_input_files(root_path):
        if format_file(tex_path):
            changed += 1
    return changed


def _apply_formatting(content: str) -> str:
    """Apply formatting rules to the given content."""
    lines = [line.rstrip() for line in content.splitlines()]
    joined = "\n".join(lines)

    joined = _JAPANESE_COMMA_RE.sub(",", joined)
    joined = _COMPAT_KANJI_RE.sub(lambda m: _COMPAT_KANJI_MAP[m.group(0)], joined)

    if content.endswith("\n"):
        joined += "\n"

    joined = _MULTI_BLANK_RE.sub("\n\n", joined)
    return joined


def _collect_input_files(root_path: Path) -> list[Path]:
    r"""Collect .tex files reachable via \input{} starting from root."""
    seen: set[Path] = set()
    result: list[Path] = []

    def visit(path: Path) -> None:
        resolved = path.resolve()
        if resolved in seen:
            return
        seen.add(resolved)
        result.append(path)

        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return

        for match in re.finditer(r"\\input\{([^}]+)\}", content):
            ref = match.group(1).strip()
            ref_path = path.parent / ref
            if not ref_path.suffix:
                ref_path = ref_path.with_suffix(".tex")
            visit(ref_path)

    visit(root_path)
    return result


@click.command()
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Root LaTeX file (main.tex, etc).",
)
def main(input_path: Path) -> None:
    changed = format_input_tree(input_path)
    if changed:
        click.echo(f"format: updated {changed} file(s)")
    else:
        click.echo("format: OK")


if __name__ == "__main__":
    main()
