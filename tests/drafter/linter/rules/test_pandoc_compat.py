"""tests/drafter/linter/rules/test_pandoc_compat.py

linter/rules/pandoc_compat.py のミラーテスト。
"""

from pathlib import Path


from drafter.common.tex_parser import Document
from drafter.linter.rules.pandoc_compat import (
    LintError,
    _check_caption_footnote,
    _check_input_files,
    _check_unlabeled_equations,
    check_pandoc_compat,
)


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def make_doc(raw: str, root: Path) -> Document:
    return Document(root_path=root, raw_content=raw)


def write_tex(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# LintError
# ---------------------------------------------------------------------------


class TestLintError:
    def test_format(self, tmp_path: Path) -> None:
        err = LintError(
            file=tmp_path / "main.tex",
            line=5,
            rule="test-rule",
            message="something wrong",
        )
        fmt = err.format()
        assert "5" in fmt
        assert "test-rule" in fmt
        assert "something wrong" in fmt


# ---------------------------------------------------------------------------
# _check_caption_footnote
# ---------------------------------------------------------------------------


class TestCheckCaptionFootnote:
    def test_no_error_when_clean(self, tmp_path: Path) -> None:
        root = write_tex(tmp_path, "main.tex", "\\caption{normal caption}\n")
        doc = make_doc("\\caption{normal caption}\n", root)
        assert _check_caption_footnote(doc) == []

    def test_detects_footnote_in_caption(self, tmp_path: Path) -> None:
        content = "\\caption{text\\footnote{note}}\n"
        root = write_tex(tmp_path, "main.tex", content)
        doc = make_doc(content, root)
        errors = _check_caption_footnote(doc)
        assert len(errors) == 1
        assert "caption-footnote" in errors[0].rule

    def test_error_reports_correct_line(self, tmp_path: Path) -> None:
        content = "line1\nline2\n\\caption{x\\footnote{y}}\nline4\n"
        root = write_tex(tmp_path, "main.tex", content)
        doc = make_doc(content, root)
        errors = _check_caption_footnote(doc)
        assert errors[0].line == 3


# ---------------------------------------------------------------------------
# _check_unlabeled_equations
# ---------------------------------------------------------------------------


class TestCheckUnlabeledEquations:
    def test_no_error_when_labeled(self, tmp_path: Path) -> None:
        content = "\\begin{equation}\n\\label{eq:1}\nx=1\n\\end{equation}\n"
        root = write_tex(tmp_path, "main.tex", content)
        doc = make_doc(content, root)
        assert _check_unlabeled_equations(doc) == []

    def test_detects_unlabeled_equation(self, tmp_path: Path) -> None:
        content = "\\begin{equation}\nx=1\n\\end{equation}\n"
        root = write_tex(tmp_path, "main.tex", content)
        doc = make_doc(content, root)
        errors = _check_unlabeled_equations(doc)
        assert len(errors) == 1
        assert "unlabeled-equation" in errors[0].rule

    def test_multiple_equations_each_checked(self, tmp_path: Path) -> None:
        content = (
            "\\begin{equation}\nx=1\n\\end{equation}\n\\begin{equation}\ny=2\n\\end{equation}\n"
        )
        root = write_tex(tmp_path, "main.tex", content)
        doc = make_doc(content, root)
        errors = _check_unlabeled_equations(doc)
        assert len(errors) == 2


# ---------------------------------------------------------------------------
# _check_input_files
# ---------------------------------------------------------------------------


class TestCheckInputFiles:
    def test_no_error_when_file_exists(self, tmp_path: Path) -> None:
        write_tex(tmp_path, "child.tex", "content")
        root = write_tex(tmp_path, "main.tex", "\\input{child}\n")
        doc = make_doc("content", root)
        assert _check_input_files(doc) == []

    def test_detects_missing_input_file(self, tmp_path: Path) -> None:
        root = write_tex(tmp_path, "main.tex", "\\input{missing}\n")
        doc = make_doc("", root)
        errors = _check_input_files(doc)
        assert len(errors) == 1
        assert "missing-input" in errors[0].rule

    def test_extension_added_automatically(self, tmp_path: Path) -> None:
        write_tex(tmp_path, "sec.tex", "text")
        root = write_tex(tmp_path, "main.tex", "\\input{sec}\n")
        doc = make_doc("text", root)
        assert _check_input_files(doc) == []


# ---------------------------------------------------------------------------
# check_pandoc_compat (統合)
# ---------------------------------------------------------------------------


class TestCheckPandocCompat:
    def test_clean_document_returns_no_errors(self, tmp_path: Path) -> None:
        root = write_tex(tmp_path, "main.tex", "\\section{intro}\nhello\n")
        doc = make_doc("\\section{intro}\nhello\n", root)
        errors = check_pandoc_compat(doc)
        assert errors == []

    def test_returns_list_of_lint_errors(self, tmp_path: Path) -> None:
        content = "\\begin{equation}\nx=1\n\\end{equation}\n"
        root = write_tex(tmp_path, "main.tex", content)
        doc = make_doc(content, root)
        errors = check_pandoc_compat(doc)
        assert all(isinstance(e, LintError) for e in errors)
