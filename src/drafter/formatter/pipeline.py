"""Common LaTeX formatting pipeline."""

from __future__ import annotations

import re
from pathlib import Path

import click

# Collapse 3+ consecutive blank lines into 2.
_MULTI_BLANK_RE = re.compile(r"\n{3,}")

# Normalize full-width Japanese punctuation to ASCII.
_JAPANESE_PUNCT_MAP: dict[str, str] = {
    "、": ",",  # U+3001 ideographic comma
    "，": ",",  # U+FF0C fullwidth comma
    "。": ".",  # U+3002 ideographic full stop
    "．": ".",  # U+FF0E fullwidth full stop
}
_JAPANESE_PUNCT_RE = re.compile("|".join(map(re.escape, _JAPANESE_PUNCT_MAP)))

# Normalize compatibility CJK radicals to common kanji.
_COMPAT_KANJI_MAP: dict[str, str] = {
    "⼦": "子",
    "⼒": "力",
    "⾜": "足",
    "⽐": "比",
    "⽬": "目",
}
_COMPAT_KANJI_RE = re.compile("|".join(map(re.escape, _COMPAT_KANJI_MAP)))

# Full-width space (U+3000) is removed entirely.
_FULLWIDTH_SPACE_RE = re.compile("　")

# A comma/period immediately followed by a non-space character.
_PUNCT_SPACE_RE = re.compile(r"[,.](?=\S)")


def _is_cjk(ch: str) -> bool:
    """Return True for Japanese script characters (kana / kanji / fullwidth)."""
    if not ch:
        return False
    o = ord(ch)
    return (
        0x3040 <= o <= 0x30FF  # Hiragana + Katakana
        or 0x3400 <= o <= 0x9FFF  # CJK Unified Ideographs (incl. ext. A)
        or 0xF900 <= o <= 0xFAFF  # CJK Compatibility Ideographs
        or 0xFF00 <= o <= 0xFFEF  # Halfwidth / Fullwidth Forms
    )


def _space_after_punct(text: str) -> str:
    r"""Insert a single ASCII space after ``,`` / ``.`` in Japanese prose.

    A space is added only when the character on either side of the punctuation
    is a Japanese (CJK) character. This keeps ASCII contexts such as file paths
    (``05-conclusion.tex``), LaTeX commands (``Fig.\ref``) and decimals
    (``0.2`` / ``1,000``) untouched. End-of-line punctuation is unaffected
    because a newline is whitespace for the ``(?=\S)`` lookahead.
    """

    def repl(m: re.Match[str]) -> str:
        i = m.start()
        before = text[i - 1] if i > 0 else ""
        after = text[m.end()]  # guaranteed to exist by the (?=\S) lookahead
        # Keep the "Fig." abbreviation glued to its reference (e.g. Fig.\ref).
        if m.group(0) == "." and text[max(0, i - 3) : i] == "Fig":
            return m.group(0)
        if _is_cjk(before) or _is_cjk(after):
            return m.group(0) + " "
        return m.group(0)

    return _PUNCT_SPACE_RE.sub(repl, text)


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

    joined = _FULLWIDTH_SPACE_RE.sub("", joined)
    joined = _JAPANESE_PUNCT_RE.sub(lambda m: _JAPANESE_PUNCT_MAP[m.group(0)], joined)
    joined = _space_after_punct(joined)
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
