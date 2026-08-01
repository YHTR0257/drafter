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

# Commands whose arguments are identifiers, paths or key=value options rather
# than prose. Inserting a space there breaks references and file paths, so
# their arguments are excluded from spacing. Prose-bearing commands such as
# \section and \caption are deliberately absent: their text is formatted.
_VERBATIM_ARG_COMMANDS = frozenset(
    {
        "input",
        "include",
        "includegraphics",
        "graphicspath",
        "label",
        "ref",
        "eqref",
        "pageref",
        "autoref",
        "cite",
        "citep",
        "citet",
        "citealp",
        "citealt",
        "citeauthor",
        "citeyear",
        "citenum",
        "nocite",
        "bibliography",
        "bibliographystyle",
        "usepackage",
        "RequirePackage",
        "documentclass",
        "setmainfont",
        "setsansfont",
        "setmonofont",
        "setmainjfont",
        "setsansjfont",
        "setmonojfont",
        "newfontfamily",
        "url",
        "href",
        "path",
    }
)

_COMMAND_RE = re.compile(r"\\([A-Za-z]+)")
_GROUP_DELIMITERS = {"{": "}", "[": "]"}


def _closing_delimiter(text: str, start: int) -> int | None:
    """Return the index closing the group opened at ``start``, or None.

    Handles nesting and backslash escapes, so ``{{a}{b}}`` and ``\\{`` are
    counted correctly.
    """
    opening = text[start]
    closing = _GROUP_DELIMITERS[opening]
    depth = 0
    index = start
    while index < len(text):
        char = text[index]
        if char == "\\":
            index += 2  # escaped character: neither delimiter nor content
            continue
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def _verbatim_arg_spans(text: str) -> list[tuple[int, int]]:
    r"""Return (start, end) index pairs covering non-prose command arguments.

    Only groups written immediately after the command name are collected, so a
    ``[`` that merely follows a command elsewhere in the sentence is not
    mistaken for an optional argument. Multi-line arguments such as the
    fontspec options of ``\setmainfont{...}[...]`` are covered.
    """
    spans: list[tuple[int, int]] = []
    for match in _COMMAND_RE.finditer(text):
        if match.group(1) not in _VERBATIM_ARG_COMMANDS:
            continue
        index = match.end()
        while index < len(text) and text[index] in _GROUP_DELIMITERS:
            end = _closing_delimiter(text, index)
            if end is None:
                break
            spans.append((index, end))
            index = end + 1
    return spans


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

    Arguments of identifier/path commands are skipped as well, so a Japanese
    file name or label such as ``\includegraphics{図.jpg}`` survives even
    though it does have a CJK character next to the punctuation.
    """
    protected = _verbatim_arg_spans(text)

    def repl(m: re.Match[str]) -> str:
        i = m.start()
        if any(start <= i <= end for start, end in protected):
            return m.group(0)
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
