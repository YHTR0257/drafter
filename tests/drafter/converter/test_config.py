"""tests/drafter/converter/test_config.py

converter/config.py のミラーテスト。
"""

import os
from pathlib import Path

from drafter.converter.config import (
    build_expanded_tex_path,
    build_pandoc_command,
    load_pandoc_defaults,
)


# ---------------------------------------------------------------------------
# load_pandoc_defaults
# ---------------------------------------------------------------------------


class TestLoadPandocDefaults:
    def test_returns_empty_dict_when_file_missing(self, tmp_path: Path) -> None:
        result = load_pandoc_defaults(tmp_path / "nonexistent.yaml")
        assert result == {}

    def test_returns_dict_from_valid_yaml(self, tmp_path: Path) -> None:
        f = tmp_path / "defaults.yaml"
        f.write_text("from: latex\nto: docx\n", encoding="utf-8")
        result = load_pandoc_defaults(f)
        assert result == {"from": "latex", "to": "docx"}

    def test_returns_empty_dict_for_non_dict_yaml(self, tmp_path: Path) -> None:
        f = tmp_path / "defaults.yaml"
        f.write_text("- item1\n- item2\n", encoding="utf-8")
        result = load_pandoc_defaults(f)
        assert result == {}


# ---------------------------------------------------------------------------
# build_pandoc_command
# ---------------------------------------------------------------------------


class TestBuildPandocCommand:
    def test_basic_command_structure(self, tmp_path: Path) -> None:
        input_path = tmp_path / "main.tex"
        output = tmp_path / "dist/main.docx"
        cmd = build_pandoc_command(input_path, output, [], None, None)
        assert cmd[0] == "pandoc"
        assert str(input_path) in cmd
        assert "-o" in cmd
        assert str(output) in cmd

    def test_bibliography_added(self, tmp_path: Path) -> None:
        bib = tmp_path / "refs.bib"
        cmd = build_pandoc_command(
            tmp_path / "main.tex",
            tmp_path / "out.docx",
            [bib],
            None,
            None,
        )
        assert any(f"--bibliography={bib}" in c for c in cmd)

    def test_multiple_bibliographies(self, tmp_path: Path) -> None:
        bibs = [tmp_path / "a.bib", tmp_path / "b.bib"]
        cmd = build_pandoc_command(tmp_path / "main.tex", tmp_path / "out.docx", bibs, None, None)
        bib_flags = [c for c in cmd if c.startswith("--bibliography=")]
        assert len(bib_flags) == 2

    def test_reference_doc_added_when_template_given(self, tmp_path: Path) -> None:
        template = tmp_path / "template.docx"
        cmd = build_pandoc_command(tmp_path / "main.tex", tmp_path / "out.docx", [], template, None)
        assert any(f"--reference-doc={template}" in c for c in cmd)

    def test_no_reference_doc_when_template_none(self, tmp_path: Path) -> None:
        cmd = build_pandoc_command(tmp_path / "main.tex", tmp_path / "out.docx", [], None, None)
        assert not any("--reference-doc" in c for c in cmd)

    def test_defaults_added_when_file_exists(self, tmp_path: Path) -> None:
        defaults = tmp_path / "defaults.yaml"
        defaults.write_text("from: latex\n", encoding="utf-8")
        cmd = build_pandoc_command(tmp_path / "main.tex", tmp_path / "out.docx", [], None, defaults)
        assert "--defaults" in cmd

    def test_defaults_not_added_when_file_missing(self, tmp_path: Path) -> None:
        defaults = tmp_path / "nonexistent.yaml"
        cmd = build_pandoc_command(tmp_path / "main.tex", tmp_path / "out.docx", [], None, defaults)
        assert "--defaults" not in cmd

    def test_citeproc_added_when_bibliography_present(self, tmp_path: Path) -> None:
        bib = tmp_path / "refs.bib"
        cmd = build_pandoc_command(tmp_path / "main.tex", tmp_path / "out.docx", [bib], None, None)
        assert "--citeproc" in cmd

    def test_citeproc_not_added_when_no_bibliography(self, tmp_path: Path) -> None:
        cmd = build_pandoc_command(tmp_path / "main.tex", tmp_path / "out.docx", [], None, None)
        assert "--citeproc" not in cmd

    def test_resource_path_joined_into_single_flag(self, tmp_path: Path) -> None:
        paths = [Path("."), Path("../../figures")]
        cmd = build_pandoc_command(
            tmp_path / "main.tex", tmp_path / "out.docx", [], None, None, paths
        )
        flags = [c for c in cmd if c.startswith("--resource-path=")]
        assert flags == [f"--resource-path=.{os.pathsep}../../figures"]

    def test_resource_path_omitted_when_empty(self, tmp_path: Path) -> None:
        empty: list[list[Path] | None] = [[], None]
        for resource_path in empty:
            cmd = build_pandoc_command(
                tmp_path / "main.tex", tmp_path / "out.docx", [], None, None, resource_path
            )
            assert not any(c.startswith("--resource-path") for c in cmd)


# ---------------------------------------------------------------------------
# build_expanded_tex_path
# ---------------------------------------------------------------------------


class TestBuildExpandedTexPath:
    def test_derives_sibling_tex_from_output(self) -> None:
        assert build_expanded_tex_path(Path("dist/main.docx")) == Path("dist/main.expanded.tex")

    def test_review_output_gets_its_own_intermediate(self) -> None:
        """docx と review-docx を並列生成しても中間ファイルが衝突しないこと。"""
        docx = build_expanded_tex_path(Path("dist/main.docx"))
        review = build_expanded_tex_path(Path("dist/main-review.docx"))
        assert review == Path("dist/main-review.expanded.tex")
        assert docx != review

    def test_stays_in_the_output_directory(self, tmp_path: Path) -> None:
        output = tmp_path / "dist" / "main.docx"
        assert build_expanded_tex_path(output).parent == output.parent
