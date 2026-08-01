"""tests/drafter/formatter/test_pipeline.py

formatter/pipeline.py のミラーテスト。
"""

from pathlib import Path

from drafter.formatter.pipeline import _apply_formatting, format_file


# ---------------------------------------------------------------------------
# _apply_formatting (内部関数)
# ---------------------------------------------------------------------------


class TestApplyFormatting:
    def test_removes_trailing_spaces(self) -> None:
        result = _apply_formatting("hello   \nworld  \n")
        assert result == "hello\nworld\n"

    def test_replaces_japanese_comma(self) -> None:
        result = _apply_formatting("あ、い\n")
        assert result == "あ, い\n"

    def test_replaces_fullwidth_comma(self) -> None:
        result = _apply_formatting("あ，い\n")
        assert result == "あ, い\n"

    def test_replaces_ideographic_period(self) -> None:
        result = _apply_formatting("あ。い\n")
        assert result == "あ. い\n"

    def test_replaces_fullwidth_period(self) -> None:
        result = _apply_formatting("あ．い\n")
        assert result == "あ. い\n"

    def test_replaces_compat_kanji(self) -> None:
        result = _apply_formatting("原⼦と⼒学\n")
        assert result == "原子と力学\n"

    def test_removes_fullwidth_space(self) -> None:
        result = _apply_formatting("　図3に示す\n")
        assert result == "図3に示す\n"

    def test_space_after_comma(self) -> None:
        result = _apply_formatting("あ,い\n")
        assert result == "あ, い\n"

    def test_space_after_period(self) -> None:
        result = _apply_formatting("示す.また\n")
        assert result == "示す. また\n"

    def test_ascii_filename_not_spaced(self) -> None:
        # File paths / extensions must stay intact (no CJK neighbours).
        result = _apply_formatting("\\input{sections/05-conclusion.tex}\n")
        assert result == "\\input{sections/05-conclusion.tex}\n"

    def test_fig_abbreviation_not_spaced(self) -> None:
        result = _apply_formatting("Fig.\\ref{fig:a}に示す\n")
        assert result == "Fig.\\ref{fig:a}に示す\n"

    def test_fig_before_cjk_not_spaced(self) -> None:
        result = _apply_formatting("Fig.また\n")
        assert result == "Fig.また\n"

    def test_decimal_point_preserved(self) -> None:
        result = _apply_formatting("$\\nu$が0.2以下\n")
        assert result == "$\\nu$が0.2以下\n"

    def test_thousands_separator_preserved(self) -> None:
        result = _apply_formatting("1,000個\n")
        assert result == "1,000個\n"

    def test_existing_space_after_comma_not_doubled(self) -> None:
        result = _apply_formatting("$C_{11}$, $C_{12}$\n")
        assert result == "$C_{11}$, $C_{12}$\n"

    def test_end_of_line_period_not_spaced(self) -> None:
        result = _apply_formatting("示した.\n")
        assert result == "示した.\n"

    def test_fullwidth_period_gets_spaced(self) -> None:
        result = _apply_formatting("示す．また\n")
        assert result == "示す. また\n"

    def test_spacing_is_idempotent(self) -> None:
        once = _apply_formatting("示す.また,示した.\n")
        twice = _apply_formatting(once)
        assert once == twice


class TestVerbatimArgumentProtection:
    """識別子・パスを引数に取るコマンドは整形の対象外にする。

    ASCII だけの引数は CJK 判定で既に守られるが、和文のファイル名・ラベル・
    引用キーは約物に CJK が隣接するため、コマンド単位の保護が要る。
    """

    def test_japanese_file_name_not_spaced(self) -> None:
        result = _apply_formatting("\\includegraphics{図.jpg}\n")
        assert result == "\\includegraphics{図.jpg}\n"

    def test_japanese_label_not_spaced(self) -> None:
        result = _apply_formatting("\\label{式.1}\n")
        assert result == "\\label{式.1}\n"

    def test_japanese_cite_key_not_spaced(self) -> None:
        result = _apply_formatting("\\cite{メタ,材料}\n")
        assert result == "\\cite{メタ,材料}\n"

    def test_nested_braces_are_covered(self) -> None:
        result = _apply_formatting("\\graphicspath{{../../figures/}}\n")
        assert result == "\\graphicspath{{../../figures/}}\n"

    def test_multiline_optional_argument_is_covered(self) -> None:
        """実際に壊れた fontspec のオプション引数。複数行にまたがる。"""
        source = (
            "\\setmainfont{Times New Roman}[\n"
            "  Path=/workspace/.devcontainer/fonts/,\n"
            "  Extension=.ttf,\n"
            "]\n"
        )
        assert _apply_formatting(source) == source

    def test_prose_commands_are_still_formatted(self) -> None:
        """\\caption や \\section の中身は本文なので整形する。"""
        result = _apply_formatting("\\caption{球は原子を,円柱は相互作用を模倣する.}\n")
        assert result == "\\caption{球は原子を, 円柱は相互作用を模倣する. }\n"

    def test_prose_after_a_protected_command_is_formatted(self) -> None:
        result = _apply_formatting("図は\\ref{fig:a}に示す.また\n")
        assert result == "図は\\ref{fig:a}に示す. また\n"

    def test_bracket_later_in_the_sentence_is_not_an_argument(self) -> None:
        """引数として隣接していない [ を光学引数と誤認しないこと。"""
        result = _apply_formatting("\\cite{a} と [注],これを示す\n")
        assert result == "\\cite{a} と [注], これを示す\n"

    def test_unbalanced_brace_does_not_hang(self) -> None:
        result = _apply_formatting("\\label{式.1\n")
        assert isinstance(result, str)

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


class TestFormatInputTree:
    def test_formats_root_and_inputs(self, tmp_path: Path) -> None:
        child = tmp_path / "sections"
        child.mkdir()
        main = tmp_path / "main.tex"
        part = child / "method.tex"

        main.write_text("\\input{sections/method}\nルート、本文\n", encoding="utf-8")
        part.write_text("子、本文\n", encoding="utf-8")

        from drafter.formatter.pipeline import format_input_tree

        changed = format_input_tree(main)

        assert changed == 2
        assert main.read_text(encoding="utf-8") == "\\input{sections/method}\nルート, 本文\n"
        assert part.read_text(encoding="utf-8") == "子, 本文\n"
