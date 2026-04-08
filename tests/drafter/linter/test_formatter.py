"""tests/drafter/linter/test_formatter.py

linter/formatter.py のミラーテスト。
"""

from pathlib import Path

from drafter.linter.formatter import _apply_formatting, format_file


# ---------------------------------------------------------------------------
# _apply_formatting (内部関数)
# ---------------------------------------------------------------------------


class TestApplyFormatting:
    def test_removes_trailing_spaces(self) -> None:
        result = _apply_formatting("hello   \nworld  \n")
        assert result == "hello\nworld\n"

    def test_collapses_triple_blank_lines(self) -> None:
        result = _apply_formatting("a\n\n\n\nb\n")
        assert result == "a\n\nb\n"

    def test_double_blank_lines_kept(self) -> None:
        result = _apply_formatting("a\n\n\nb\n")
        # 3行 → 2行
        assert result == "a\n\nb\n"

    def test_single_blank_line_unchanged(self) -> None:
        result = _apply_formatting("a\n\nb\n")
        assert result == "a\n\nb\n"

    def test_preserves_trailing_newline(self) -> None:
        result = _apply_formatting("hello\n")
        assert result.endswith("\n")

    def test_no_trailing_newline_not_added(self) -> None:
        result = _apply_formatting("hello")
        assert result == "hello"

    def test_no_change_on_clean_content(self) -> None:
        content = "clean line\n\nanother\n"
        assert _apply_formatting(content) == content


# ---------------------------------------------------------------------------
# format_file
# ---------------------------------------------------------------------------


class TestFormatFile:
    def test_returns_true_when_changed(self, tmp_path: Path) -> None:
        f = tmp_path / "test.tex"
        f.write_text("line   \n", encoding="utf-8")
        assert format_file(f) is True

    def test_returns_false_when_unchanged(self, tmp_path: Path) -> None:
        f = tmp_path / "test.tex"
        f.write_text("clean line\n", encoding="utf-8")
        assert format_file(f) is False

    def test_file_is_written_when_changed(self, tmp_path: Path) -> None:
        f = tmp_path / "test.tex"
        f.write_text("line   \n", encoding="utf-8")
        format_file(f)
        assert f.read_text(encoding="utf-8") == "line\n"

    def test_file_unchanged_when_no_change(self, tmp_path: Path) -> None:
        content = "clean\n"
        f = tmp_path / "test.tex"
        f.write_text(content, encoding="utf-8")
        format_file(f)
        assert f.read_text(encoding="utf-8") == content
