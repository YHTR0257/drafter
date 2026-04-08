"""tests/drafter/common/test_tex_parser.py

common/tex_parser.py のミラーテスト。
"""

from pathlib import Path


from drafter.common.tex_parser import Document, Environment, Section, TexParser


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def write_tex(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# resolve_inputs
# ---------------------------------------------------------------------------


class TestResolveInputs:
    def test_no_input(self, tmp_path: Path) -> None:
        f = write_tex(tmp_path, "main.tex", "hello world\n")
        assert TexParser().resolve_inputs(f) == "hello world\n"

    def test_single_input_with_extension(self, tmp_path: Path) -> None:
        write_tex(tmp_path, "child.tex", "child content\n")
        f = write_tex(tmp_path, "main.tex", r"\input{child.tex}" + "\n")
        assert "child content" in TexParser().resolve_inputs(f)

    def test_single_input_without_extension(self, tmp_path: Path) -> None:
        write_tex(tmp_path, "child.tex", "child content\n")
        f = write_tex(tmp_path, "main.tex", r"\input{child}" + "\n")
        assert "child content" in TexParser().resolve_inputs(f)

    def test_nested_inputs(self, tmp_path: Path) -> None:
        write_tex(tmp_path, "grand.tex", "grand\n")
        write_tex(tmp_path, "child.tex", r"\input{grand}" + "\n")
        f = write_tex(tmp_path, "main.tex", r"\input{child}" + "\n")
        assert "grand" in TexParser().resolve_inputs(f)

    def test_missing_input_returns_error_comment(self, tmp_path: Path) -> None:
        f = write_tex(tmp_path, "main.tex", r"\input{missing}" + "\n")
        result = TexParser().resolve_inputs(f)
        assert "ERROR" in result
        assert "missing" in result


# ---------------------------------------------------------------------------
# estimate_tokens
# ---------------------------------------------------------------------------


class TestEstimateTokens:
    def test_empty(self) -> None:
        assert TexParser().estimate_tokens("") == 1  # max(1, ...)

    def test_ascii(self) -> None:
        text = "a" * 100
        assert TexParser().estimate_tokens(text) == 50

    def test_japanese(self) -> None:
        text = "あ" * 100  # 1文字3バイトだがlen()は100
        assert TexParser().estimate_tokens(text) == 50

    def test_longer_gives_more_tokens(self) -> None:
        short = TexParser().estimate_tokens("abc")
        long = TexParser().estimate_tokens("abc" * 100)
        assert long > short


# ---------------------------------------------------------------------------
# parse - Document 構造
# ---------------------------------------------------------------------------


class TestParse:
    def test_returns_document(self, tmp_path: Path) -> None:
        f = write_tex(tmp_path, "main.tex", "\\section{intro}\nhello\n")
        doc = TexParser().parse(f)
        assert isinstance(doc, Document)
        assert doc.root_path == f

    def test_raw_content_is_resolved(self, tmp_path: Path) -> None:
        write_tex(tmp_path, "sec.tex", "\\section{method}\ncontent\n")
        f = write_tex(tmp_path, "main.tex", "\\input{sec}\n")
        doc = TexParser().parse(f)
        assert "\\section{method}" in doc.raw_content

    def test_top_level_sections_extracted(self, tmp_path: Path) -> None:
        f = write_tex(
            tmp_path,
            "main.tex",
            "\\section{intro}\nA\n\\section{method}\nB\n",
        )
        doc = TexParser().parse(f)
        titles = [s.title for s in doc.sections]
        assert titles == ["intro", "method"]

    def test_chapter_level(self, tmp_path: Path) -> None:
        f = write_tex(tmp_path, "main.tex", "\\chapter{chap1}\ntext\n")
        doc = TexParser().parse(f)
        assert len(doc.sections) == 1
        assert doc.sections[0].level == "chapter"

    def test_subsection_becomes_child(self, tmp_path: Path) -> None:
        f = write_tex(
            tmp_path,
            "main.tex",
            "\\section{intro}\nbody\n\\subsection{detail}\nmore\n",
        )
        doc = TexParser().parse(f)
        assert len(doc.sections) == 1
        sec = doc.sections[0]
        assert any(c.title == "detail" for c in sec.children)

    def test_environment_extracted(self, tmp_path: Path) -> None:
        f = write_tex(
            tmp_path,
            "main.tex",
            "\\section{result}\n\\begin{figure}\ncontent\n\\end{figure}\n",
        )
        doc = TexParser().parse(f)
        envs = doc.sections[0].environments
        assert len(envs) == 1
        assert envs[0].name == "figure"


# ---------------------------------------------------------------------------
# Section / Environment データクラス
# ---------------------------------------------------------------------------


class TestDataclasses:
    def test_section_defaults(self) -> None:
        sec = Section(level="section", title="t", content="c")
        assert sec.children == []
        assert sec.environments == []

    def test_environment_fields(self) -> None:
        env = Environment(name="equation", content="x=1", line_start=1, line_end=3)
        assert env.name == "equation"
        assert env.line_end == 3
