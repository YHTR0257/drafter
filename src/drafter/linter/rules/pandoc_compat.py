"""Pandoc互換性チェックルール。

Pandoc が LaTeX → DOCX 変換時に問題を起こしやすいパターンを検出する。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from drafter.common.tex_parser import Document

# \\newcommand{\\foo} または \\renewcommand{\\foo} でマクロ定義
_NEWCOMMAND_RE = re.compile(r"\\(?:new|renew)command\{(\\[a-zA-Z]+)\}")

# \\begin{equation} に \\label がない
_EQUATION_BEGIN_RE = re.compile(r"\\begin\{equation\}")
_LABEL_RE = re.compile(r"\\label\{[^}]+\}")

# キャプション内の \\footnote
_CAPTION_FOOTNOTE_RE = re.compile(r"\\caption\{[^}]*\\footnote\{")

# \\input{file} の参照
_INPUT_RE = re.compile(r"\\input\{([^}]+)\}")


@dataclass
class LintError:
    """1件のlintエラー。"""

    file: Path
    line: int
    rule: str
    message: str

    def format(self) -> str:
        """人間が読める形式に変換する。"""
        return f"{self.file}:{self.line}: [{self.rule}] {self.message}"


def check_pandoc_compat(document: Document) -> list[LintError]:
    """Pandoc互換性に関するチェックを全て実行し、エラーリストを返す。"""
    errors: list[LintError] = []
    errors.extend(_check_input_files(document))
    errors.extend(_check_caption_footnote(document))
    errors.extend(_check_unlabeled_equations(document))
    errors.extend(_check_undefined_macros(document))
    return errors


# ------------------------------------------------------------------
# 個別チェック
# ------------------------------------------------------------------


def _check_input_files(document: Document) -> list[LintError]:
    """\\input{} で参照するファイルの存在を確認する。"""
    errors: list[LintError] = []
    lines = document.raw_content.splitlines()

    # root ファイルを起点にして、元のファイルの \\input を再スキャン
    root_content = document.root_path.read_text(encoding="utf-8")
    root_lines = root_content.splitlines()

    for lineno, line in enumerate(root_lines, 1):
        for m in _INPUT_RE.finditer(line):
            ref = m.group(1).strip()
            ref_path = document.root_path.parent / ref
            if not ref_path.suffix:
                ref_path = ref_path.with_suffix(".tex")
            if not ref_path.exists():
                errors.append(
                    LintError(
                        file=document.root_path,
                        line=lineno,
                        rule="pandoc-compat/missing-input",
                        message=f"\\input が参照するファイルが存在しません: {ref_path}",
                    )
                )
    _ = lines  # raw_content も保持しているが今は root のみチェック
    return errors


def _check_caption_footnote(document: Document) -> list[LintError]:
    """キャプション内の \\footnote を検出する（Pandoc非対応）。"""
    errors: list[LintError] = []
    for lineno, line in enumerate(document.raw_content.splitlines(), 1):
        if _CAPTION_FOOTNOTE_RE.search(line):
            errors.append(
                LintError(
                    file=document.root_path,
                    line=lineno,
                    rule="pandoc-compat/caption-footnote",
                    message=(
                        "\\caption 内の \\footnote は Pandoc で変換できません。"
                        " 脚注をキャプション外に移動してください。"
                    ),
                )
            )
    return errors


def _check_unlabeled_equations(document: Document) -> list[LintError]:
    """ラベルのない equation 環境を検出する。"""
    errors: list[LintError] = []
    lines = document.raw_content.splitlines()
    i = 0
    while i < len(lines):
        if _EQUATION_BEGIN_RE.search(lines[i]):
            # equation ブロック内に \\label があるか確認
            block_lines = [lines[i]]
            j = i + 1
            while j < len(lines):
                block_lines.append(lines[j])
                if r"\end{equation}" in lines[j]:
                    break
                j += 1
            block = "\n".join(block_lines)
            if not _LABEL_RE.search(block):
                errors.append(
                    LintError(
                        file=document.root_path,
                        line=i + 1,
                        rule="pandoc-compat/unlabeled-equation",
                        message=(
                            "\\label のない equation 環境があります。"
                            " 相互参照のために \\label を追加することを推奨します。"
                        ),
                    )
                )
            i = j + 1
            continue
        i += 1
    return errors


def _check_undefined_macros(document: Document) -> list[LintError]:
    """\\newcommand で定義されていないカスタムマクロを検出する。

    標準LaTeXコマンドは除外し、ユーザー定義と思われる \\[a-z]+ 形式のみを対象とする。
    """
    errors: list[LintError] = []
    content = document.raw_content

    # 定義済みマクロを収集
    defined: set[str] = set()
    for m in _NEWCOMMAND_RE.finditer(content):
        defined.add(m.group(1))

    if not defined:
        return errors  # カスタムマクロなし

    # 使用箇所をチェック（定義済みでないものを報告）
    # 既知の標準コマンドリストと照合する簡易実装
    for lineno, line in enumerate(content.splitlines(), 1):
        for m in re.finditer(r"\\([a-zA-Z]+)", line):
            cmd = f"\\{m.group(1)}"
            if cmd in _STANDARD_COMMANDS:
                continue
            if cmd not in defined and _looks_like_custom(m.group(1)):
                errors.append(
                    LintError(
                        file=document.root_path,
                        line=lineno,
                        rule="pandoc-compat/undefined-macro",
                        message=(
                            f"{cmd} は \\newcommand で定義されていない可能性があります。"
                            " Pandoc での変換時にエラーになる場合があります。"
                        ),
                    )
                )
                defined.add(cmd)  # 同じコマンドは1度だけ報告
    return errors


def _looks_like_custom(name: str) -> bool:
    """コマンド名がユーザー定義っぽいか判定する（ヒューリスティック）。"""
    # 全小文字 or キャメルケースで、短いものは標準コマンドとみなす
    return len(name) > 3 and not name.islower()


# よく使う標準LaTeXコマンド（False positive 抑制用）
_STANDARD_COMMANDS: frozenset[str] = frozenset(
    {
        "\\documentclass",
        "\\usepackage",
        "\\begin",
        "\\end",
        "\\section",
        "\\subsection",
        "\\subsubsection",
        "\\chapter",
        "\\input",
        "\\include",
        "\\label",
        "\\ref",
        "\\cite",
        "\\textbf",
        "\\textit",
        "\\emph",
        "\\text",
        "\\frac",
        "\\sqrt",
        "\\sum",
        "\\int",
        "\\prod",
        "\\alpha",
        "\\beta",
        "\\gamma",
        "\\delta",
        "\\epsilon",
        "\\theta",
        "\\lambda",
        "\\mu",
        "\\pi",
        "\\sigma",
        "\\omega",
        "\\Gamma",
        "\\Delta",
        "\\Theta",
        "\\Lambda",
        "\\Pi",
        "\\Sigma",
        "\\Omega",
        "\\Phi",
        "\\Psi",
        "\\left",
        "\\right",
        "\\cdot",
        "\\cdots",
        "\\ldots",
        "\\mathbf",
        "\\mathrm",
        "\\mathcal",
        "\\mathbb",
        "\\includegraphics",
        "\\caption",
        "\\centering",
        "\\hline",
        "\\multicolumn",
        "\\multirow",
        "\\bibliographystyle",
        "\\bibliography",
        "\\title",
        "\\author",
        "\\date",
        "\\maketitle",
        "\\newcommand",
        "\\renewcommand",
        "\\providecommand",
        "\\setmainfont",
        "\\setmainjfont",
        "\\graphicspath",
        "\\counterwithin",
        "\\captionsetup",
        "\\renewcommand",
        "\\thechapter",
        "\\thesection",
        "\\thesubsection",
        "\\thefigure",
        "\\thetable",
        "\\bibcommenthead",
        "\\footnote",
        "\\footnotemark",
        "\\footnotetext",
        "\\item",
        "\\paragraph",
        "\\subparagraph",
        "\\nonumber",
        "\\notag",
        "\\tag",
        "\\hspace",
        "\\vspace",
        "\\quad",
        "\\qquad",
        "\\newline",
        "\\linebreak",
        "\\pagebreak",
        "\\noindent",
        "\\indent",
        "\\today",
        "\\par",
    }
)
