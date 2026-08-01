"""drafter.converter.word_template のテスト。

期待値は `templates/msword/ref/Graduation_paper_split.docx` で実際に使われている
スタイル（テーマ参照を解決した実効値）に対応する。
"""

from __future__ import annotations

import io
import zipfile
from xml.etree import ElementTree as ET

import pytest

from drafter.converter.word_template import (
    ALL_SPECS,
    ARTICLE_SPEC,
    BODY_EN_FONT,
    BODY_JA_FONT,
    BODY_SIZE,
    COMPACT_BODY_SIZE,
    DOUBLE_LINE,
    FIRST_LINE_INDENT,
    HEADING_EN_FONT,
    HEADING_JA_FONT,
    HEADING_NUM_ID,
    PAGE_MARGIN,
    PAGE_WIDTH,
    REFERENCE_LINE_PITCH,
    REVIEW_SPEC,
    SHORT_SPEC,
    COLUMN_SPACE,
    SUB_HEADING_SIZE,
    TIGHT_LINE_PITCH,
    TOP_HEADING_SIZE,
    W_NS,
    ParagraphFormat,
    RunFormat,
    TemplateSpec,
    apply_heading_numbering,
    apply_section_properties,
    apply_style_overrides,
    apply_theme_fonts,
    build_heading_numbering,
    build_paragraph_properties,
    build_run_properties,
    build_section_properties,
    build_style_overrides,
    build_template,
)

# `w:pPr` / `w:rPr` / `w:sectPr` の子要素はスキーマ順が決まっており、崩れると
# Word がファイルを破損扱いにする。実装が守るべき順序をテスト側にも明記しておく。
P_PR_ORDER = [
    "keepNext",
    "keepLines",
    "pageBreakBefore",
    "widowControl",
    "numPr",
    "snapToGrid",
    "spacing",
    "ind",
    "jc",
    "outlineLvl",
]
R_PR_ORDER = ["rFonts", "b", "bCs", "color", "sz", "szCs"]
SECT_PR_ORDER = ["footnotePr", "pgSz", "pgMar", "lnNumType", "cols", "docGrid"]


def _tag(element: ET.Element) -> str:
    """完全修飾名から `w:` 名前空間を取り除いたローカル名を返す。"""
    return element.tag.removeprefix(f"{{{W_NS}}}")


def _attr(element: ET.Element, name: str) -> str | None:
    return element.get(f"{{{W_NS}}}{name}")


def _find(root: ET.Element, path: str) -> ET.Element:
    found = root.find(path.replace("w:", f"{{{W_NS}}}"))
    assert found is not None, f"element not found: {path}"
    return found


def _style(styles_root: ET.Element, style_id: str) -> ET.Element:
    for style in styles_root.findall(f"{{{W_NS}}}style"):
        if _attr(style, "styleId") == style_id:
            return style
    raise AssertionError(f"style not found: {style_id}")


def _minimal_styles_xml() -> bytes:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<w:styles xmlns:w="{W_NS}">
  <w:docDefaults>
    <w:rPrDefault>
      <w:rPr><w:rFonts w:asciiTheme="minorHAnsi"/><w:sz w:val="24"/></w:rPr>
    </w:rPrDefault>
    <w:pPrDefault>
      <w:pPr><w:spacing w:after="200"/></w:pPr>
    </w:pPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
  <w:style w:type="paragraph" w:styleId="BodyText"><w:name w:val="Body Text"/></w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:rPr><w:color w:val="0F4761"/><w:sz w:val="40"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Unmanaged">
    <w:name w:val="Unmanaged"/>
    <w:rPr><w:sz w:val="99"/></w:rPr>
  </w:style>
</w:styles>""".encode()


def _minimal_document_xml() -> bytes:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{W_NS}">
  <w:body>
    <w:p/>
    <w:sectPr><w:footnotePr><w:numRestart w:val="eachSect"/></w:footnotePr></w:sectPr>
  </w:body>
</w:document>""".encode()


def _minimal_numbering_xml() -> bytes:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<w:numbering xmlns:w="{W_NS}">
  <w:abstractNum w:abstractNumId="990"><w:multiLevelType w:val="hybridMultilevel"/></w:abstractNum>
  <w:num w:numId="1000"><w:abstractNumId w:val="990"/></w:num>
</w:numbering>""".encode()


def _minimal_docx() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/styles.xml", _minimal_styles_xml())
        archive.writestr("word/document.xml", _minimal_document_xml())
        archive.writestr("word/numbering.xml", _minimal_numbering_xml())
        archive.writestr("[Content_Types].xml", "<Types/>")
    return buffer.getvalue()


# ============================================================
# build_paragraph_properties
# ============================================================


def test_build_paragraph_properties_emits_schema_order() -> None:
    p_pr = build_paragraph_properties(
        ParagraphFormat(
            keep_next=True,
            keep_lines=True,
            page_break_before=True,
            widow_control_off=True,
            numbering_level=0,
            snap_to_grid=False,
            space_before=280,
            space_after=280,
            line=480,
            indent_first_line=227,
            justification="both",
            outline_level=0,
        )
    )
    assert [_tag(child) for child in p_pr] == P_PR_ORDER


def test_build_paragraph_properties_omits_unset_fields() -> None:
    p_pr = build_paragraph_properties(ParagraphFormat(justification="center"))
    assert [_tag(child) for child in p_pr] == ["jc"]


def test_build_paragraph_properties_zero_indent_is_emitted() -> None:
    """字下げ 0 は「未指定」ではなく「継承元の字下げを打ち消す」指定。"""
    p_pr = build_paragraph_properties(ParagraphFormat(indent_first_line=0))
    assert _attr(_find(p_pr, "w:ind"), "firstLine") == "0"


def test_build_paragraph_properties_numbering_links_to_heading_num_id() -> None:
    num_pr = _find(build_paragraph_properties(ParagraphFormat(numbering_level=2)), "w:numPr")
    assert _attr(_find(num_pr, "w:ilvl"), "val") == "2"
    assert _attr(_find(num_pr, "w:numId"), "val") == HEADING_NUM_ID


def test_build_paragraph_properties_line_spacing_uses_auto_rule() -> None:
    spacing = _find(build_paragraph_properties(ParagraphFormat(line=DOUBLE_LINE)), "w:spacing")
    assert (_attr(spacing, "line"), _attr(spacing, "lineRule")) == ("480", "auto")


# ============================================================
# build_run_properties
# ============================================================


def test_build_run_properties_emits_schema_order() -> None:
    r_pr = build_run_properties(RunFormat(bold=True, size=28, color="000000", heading_fonts=True))
    assert [_tag(child) for child in r_pr] == R_PR_ORDER


def test_build_run_properties_body_uses_mincho_and_times() -> None:
    fonts = _find(build_run_properties(RunFormat(body_fonts=True)), "w:rFonts")
    assert _attr(fonts, "eastAsia") == BODY_JA_FONT
    assert _attr(fonts, "ascii") == BODY_EN_FONT
    assert _attr(fonts, "hAnsi") == BODY_EN_FONT


def test_build_run_properties_heading_uses_gothic_and_arial() -> None:
    """参考 docx は本文=明朝 / 見出し=ゴシックの対比で見出しを目立たせている。"""
    fonts = _find(build_run_properties(RunFormat(heading_fonts=True)), "w:rFonts")
    assert _attr(fonts, "eastAsia") == HEADING_JA_FONT
    assert _attr(fonts, "ascii") == HEADING_EN_FONT


def test_build_run_properties_uses_explicit_fonts_not_theme() -> None:
    """テーマ参照だと環境によってフォントが変わるため実名指定であること。"""
    fonts = _find(build_run_properties(RunFormat(body_fonts=True)), "w:rFonts")
    assert not any(key.endswith("Theme") for key in fonts.keys())


def test_build_run_properties_without_font_flags_emits_no_fonts() -> None:
    assert build_run_properties(RunFormat(size=24)).find(f"{{{W_NS}}}rFonts") is None


# ============================================================
# spec 定義
# ============================================================


def test_specs_have_distinct_filenames() -> None:
    assert len({spec.filename for spec in ALL_SPECS}) == len(ALL_SPECS) == 3


def test_spec_heading_depths_match_intended_use() -> None:
    """article=章節項の4階層、review=章のみ、short=章節の2階層。"""
    assert ARTICLE_SPEC.heading_depth == 4
    assert REVIEW_SPEC.heading_depth == 1
    assert SHORT_SPEC.heading_depth == 2


def test_only_short_spec_is_two_column() -> None:
    assert SHORT_SPEC.columns == 2
    assert ARTICLE_SPEC.columns == REVIEW_SPEC.columns == 1


def test_only_review_spec_widens_line_spacing() -> None:
    assert REVIEW_SPEC.body_line == DOUBLE_LINE
    assert ARTICLE_SPEC.body_line is None
    assert SHORT_SPEC.body_line is None


def test_short_spec_does_not_page_break_per_chapter() -> None:
    """ショートペーパーは章ごとの改ページをしない。"""
    assert SHORT_SPEC.page_break_before_chapter is False
    assert ARTICLE_SPEC.page_break_before_chapter is True


# ============================================================
# build_style_overrides
# ============================================================


@pytest.mark.parametrize("spec", ALL_SPECS)
def test_normal_is_justified_body_font(spec: TemplateSpec) -> None:
    override = build_style_overrides(spec)["Normal"]
    assert override.paragraph is not None
    assert override.paragraph.justification == "both"
    assert override.paragraph.widow_control_off is True
    assert override.run is not None
    assert override.run.size == spec.body_size
    assert override.run.body_fonts is True


def test_only_two_column_spec_shrinks_the_body_size() -> None:
    """2 段組は 1 段が狭いので 10.5pt。1 段組は参考 docx どおり 12pt。"""
    assert SHORT_SPEC.body_size == COMPACT_BODY_SIZE < BODY_SIZE
    assert ARTICLE_SPEC.body_size == REVIEW_SPEC.body_size == BODY_SIZE


def test_footnotes_are_smaller_than_body() -> None:
    for spec in ALL_SPECS:
        run = build_style_overrides(spec)["FootnoteText"].run
        assert run is not None
        assert run.size is not None and run.size < spec.body_size, spec.filename


@pytest.mark.parametrize("spec", ALL_SPECS)
def test_body_styles_use_one_character_indent(spec: TemplateSpec) -> None:
    overrides = build_style_overrides(spec)
    for style_id in ("BodyText", "FirstParagraph"):
        paragraph = overrides[style_id].paragraph
        assert paragraph is not None
        assert paragraph.indent_first_line == FIRST_LINE_INDENT


def test_first_paragraph_is_indented_like_body() -> None:
    """日本語組版では見出し直後の段落も字下げするため本文と同一書式。"""
    overrides = build_style_overrides(ARTICLE_SPEC)
    assert overrides["FirstParagraph"].paragraph == overrides["BodyText"].paragraph


def test_caption_and_bibliography_are_not_indented() -> None:
    """参考 docx の `1_Caption` / `1_citation` は Normal 継承で字下げしない。"""
    overrides = build_style_overrides(ARTICLE_SPEC)
    for style_id in ("Caption", "Bibliography", "Compact"):
        paragraph = overrides[style_id].paragraph
        assert paragraph is not None, style_id
        assert paragraph.indent_first_line == 0, style_id


def test_figure_is_centered_and_kept_with_caption() -> None:
    """参考 docx の `1_Figure` は keepNext + 中央揃え。"""
    paragraph = build_style_overrides(ARTICLE_SPEC)["Figure"].paragraph
    assert paragraph is not None
    assert paragraph.keep_next is True
    assert paragraph.justification == "center"


def test_abstract_title_is_centered_bold_body_font() -> None:
    """参考 docx の `0_見出し`（採番なし・中央揃え・明朝・太字）に対応。"""
    override = build_style_overrides(ARTICLE_SPEC)["AbstractTitle"]
    assert override.paragraph is not None
    assert override.paragraph.justification == "center"
    assert override.run is not None
    assert override.run.bold is True
    assert override.run.body_fonts is True


@pytest.mark.parametrize("spec", ALL_SPECS)
def test_review_line_spacing_only_applies_to_review(spec: TemplateSpec) -> None:
    paragraph = build_style_overrides(spec)["BodyText"].paragraph
    assert paragraph is not None
    assert paragraph.line == spec.body_line


# ============================================================
# build_heading_override（build_style_overrides 経由）
# ============================================================


@pytest.mark.parametrize("spec", ALL_SPECS)
def test_chapter_heading_is_gothic_and_largest(spec: TemplateSpec) -> None:
    run = build_style_overrides(spec)["Heading1"].run
    assert run is not None
    assert run.size == TOP_HEADING_SIZE
    assert run.heading_fonts is True
    assert run.bold is False, "参考 docx の見出しは太字を使わずゴシックで対比する"


@pytest.mark.parametrize("spec", ALL_SPECS)
def test_headings_within_depth_are_numbered(spec: TemplateSpec) -> None:
    overrides = build_style_overrides(spec)
    for level in range(1, spec.heading_depth + 1):
        paragraph = overrides[f"Heading{level}"].paragraph
        assert paragraph is not None
        assert paragraph.numbering_level == level - 1, f"Heading{level}"


@pytest.mark.parametrize("spec", ALL_SPECS)
def test_headings_beyond_depth_are_not_numbered(spec: TemplateSpec) -> None:
    overrides = build_style_overrides(spec)
    for level in range(spec.heading_depth + 1, 10):
        paragraph = overrides[f"Heading{level}"].paragraph
        assert paragraph is not None
        assert paragraph.numbering_level is None, f"Heading{level}"


@pytest.mark.parametrize("spec", ALL_SPECS)
def test_headings_beyond_depth_keep_heading_font(spec: TemplateSpec) -> None:
    """採番しない階層でも本文と見分けられるようゴシックは維持する。"""
    run = build_style_overrides(spec)[f"Heading{spec.heading_depth + 1}"].run
    assert run is not None
    assert run.heading_fonts is True
    assert run.size == SUB_HEADING_SIZE


def test_all_heading_levels_are_defined() -> None:
    overrides = build_style_overrides(ARTICLE_SPEC)
    for level in range(1, 10):
        assert f"Heading{level}" in overrides


@pytest.mark.parametrize("spec", ALL_SPECS)
def test_headings_override_pandoc_accent_color(spec: TemplateSpec) -> None:
    """Pandoc 既定の見出しは青系。論文用に黒へ戻す必要がある。"""
    overrides = build_style_overrides(spec)
    for level in range(1, 10):
        run = overrides[f"Heading{level}"].run
        assert run is not None
        assert run.color == "000000", f"Heading{level}"


def test_chapter_heading_page_break_follows_spec() -> None:
    for spec in ALL_SPECS:
        paragraph = build_style_overrides(spec)["Heading1"].paragraph
        assert paragraph is not None
        assert paragraph.page_break_before is spec.page_break_before_chapter


def test_section_headings_hang_by_number_width() -> None:
    """参考 docx の `2_見出し` は左 425・ぶら下げ 425。"""
    paragraph = build_style_overrides(ARTICLE_SPEC)["Heading2"].paragraph
    assert paragraph is not None
    assert (paragraph.indent_left, paragraph.indent_hanging) == (425, 425)


# ============================================================
# apply_style_overrides
# ============================================================


def test_apply_style_overrides_replaces_existing_properties() -> None:
    root = ET.fromstring(apply_style_overrides(_minimal_styles_xml(), ARTICLE_SPEC))
    heading = _style(root, "Heading1")
    assert len(heading.findall(f"{{{W_NS}}}rPr")) == 1
    assert _attr(_find(heading, "w:rPr/w:color"), "val") == "000000"
    assert _attr(_find(heading, "w:rPr/w:sz"), "val") == str(TOP_HEADING_SIZE)


def test_apply_style_overrides_puts_paragraph_properties_before_run_properties() -> None:
    root = ET.fromstring(apply_style_overrides(_minimal_styles_xml(), ARTICLE_SPEC))
    tags = [_tag(child) for child in _style(root, "Heading1")]
    assert tags.index("pPr") < tags.index("rPr")
    assert tags.index("name") < tags.index("pPr")


def test_apply_style_overrides_leaves_unknown_styles_untouched() -> None:
    root = ET.fromstring(apply_style_overrides(_minimal_styles_xml(), ARTICLE_SPEC))
    assert _attr(_find(_style(root, "Unmanaged"), "w:rPr/w:sz"), "val") == "99"


def test_apply_style_overrides_rewrites_doc_defaults() -> None:
    root = ET.fromstring(apply_style_overrides(_minimal_styles_xml(), ARTICLE_SPEC))
    r_pr = _find(root, "w:docDefaults/w:rPrDefault/w:rPr")
    assert _attr(_find(r_pr, "w:rFonts"), "eastAsia") == BODY_JA_FONT
    assert _attr(_find(r_pr, "w:sz"), "val") == str(BODY_SIZE)
    assert _attr(_find(r_pr, "w:lang"), "eastAsia") == "ja-JP"


def test_apply_style_overrides_clears_default_paragraph_spacing() -> None:
    """Pandoc 既定の段落後 200 が残ると行送り指定と二重にかかる。"""
    root = ET.fromstring(apply_style_overrides(_minimal_styles_xml(), ARTICLE_SPEC))
    spacing = _find(root, "w:docDefaults/w:pPrDefault/w:pPr/w:spacing")
    assert _attr(spacing, "after") == "0"


# ============================================================
# build_heading_numbering / apply_heading_numbering
# ============================================================


@pytest.mark.parametrize("spec", ALL_SPECS)
def test_numbering_links_exactly_the_designed_depth(spec: TemplateSpec) -> None:
    abstract_num, _ = build_heading_numbering(spec)
    linked = [
        _attr(p_style, "val")
        for p_style in abstract_num.iter(f"{{{W_NS}}}pStyle")
        if _attr(p_style, "val") is not None
    ]
    assert linked == [f"Heading{level}" for level in range(1, spec.heading_depth + 1)]


def test_numbering_uses_chapter_prefix_at_top_level() -> None:
    abstract_num, _ = build_heading_numbering(ARTICLE_SPEC)
    levels = abstract_num.findall(f"{{{W_NS}}}lvl")
    texts = [_attr(_find(level, "w:lvlText"), "val") for level in levels]
    assert texts == ["第%1章", "%1.%2.", "%1.%2.%3.", "%4)"]


def test_numbering_num_points_at_abstract_num() -> None:
    abstract_num, num = build_heading_numbering(ARTICLE_SPEC)
    assert _attr(num, "numId") == HEADING_NUM_ID
    assert _attr(_find(num, "w:abstractNumId"), "val") == _attr(abstract_num, "abstractNumId")


def test_apply_heading_numbering_keeps_abstract_nums_before_nums() -> None:
    """CT_Numbering は abstractNum 群 → num 群の順を要求する。"""
    root = ET.fromstring(apply_heading_numbering(_minimal_numbering_xml(), ARTICLE_SPEC))
    tags = [_tag(child) for child in root]
    assert tags == ["abstractNum", "abstractNum", "num", "num"]


def test_apply_heading_numbering_does_not_collide_with_existing_ids() -> None:
    root = ET.fromstring(apply_heading_numbering(_minimal_numbering_xml(), ARTICLE_SPEC))
    abstract_ids = [_attr(e, "abstractNumId") for e in root.findall(f"{{{W_NS}}}abstractNum")]
    num_ids = [_attr(e, "numId") for e in root.findall(f"{{{W_NS}}}num")]
    assert len(set(abstract_ids)) == len(abstract_ids)
    assert len(set(num_ids)) == len(num_ids)
    assert HEADING_NUM_ID in num_ids


# ============================================================
# build_section_properties / apply_section_properties
# ============================================================


def test_short_spec_produces_two_columns() -> None:
    cols = _find(build_section_properties(SHORT_SPEC), "w:cols")
    assert _attr(cols, "num") == "2"
    assert _attr(cols, "equalWidth") == "1"


@pytest.mark.parametrize("spec", [ARTICLE_SPEC, REVIEW_SPEC])
def test_single_column_specs_omit_column_count(spec: TemplateSpec) -> None:
    assert _attr(_find(build_section_properties(spec), "w:cols"), "num") is None


def test_review_spec_enables_line_numbers() -> None:
    """校閲時に指摘箇所を行番号で指せるようにする。"""
    assert _attr(_find(build_section_properties(REVIEW_SPEC), "w:lnNumType"), "countBy") == "1"


@pytest.mark.parametrize("spec", [ARTICLE_SPEC, SHORT_SPEC])
def test_non_review_specs_have_no_line_numbers(spec: TemplateSpec) -> None:
    assert build_section_properties(spec).find(f"{{{W_NS}}}lnNumType") is None


@pytest.mark.parametrize("spec", ALL_SPECS)
def test_section_properties_use_reference_page_size(spec: TemplateSpec) -> None:
    page_size = _find(build_section_properties(spec), "w:pgSz")
    assert (_attr(page_size, "w"), _attr(page_size, "h")) == ("11900", "16840")


@pytest.mark.parametrize("spec", ALL_SPECS)
def test_margins_are_uniform_and_narrower_than_the_reference(spec: TemplateSpec) -> None:
    """参考 docx の 1440 だと 12pt 本文で 1 行 37 字しか入らないため詰める。"""
    margins = _find(build_section_properties(spec), "w:pgMar")
    assert {_attr(margins, side) for side in ("top", "right", "bottom", "left")} == {
        str(PAGE_MARGIN)
    }
    assert PAGE_MARGIN < 1440


@pytest.mark.parametrize("spec", ALL_SPECS)
def test_line_holds_at_least_twenty_characters(spec: TemplateSpec) -> None:
    """1 行が短すぎると読みにくいので、全角 20 字を下回らないこと。"""
    text_width = PAGE_WIDTH - 2 * PAGE_MARGIN - COLUMN_SPACE * (spec.columns - 1)
    column_width = text_width / spec.columns
    characters = column_width / (spec.body_size / 2 * 20)
    assert characters >= 20, f"{spec.filename}: {characters:.1f} 字"


def test_line_grids_are_tighter_than_the_reference() -> None:
    """参考 docx の 466 は 12pt 本文で約 1.94 行ぶんと広すぎるため詰める。"""
    assert TIGHT_LINE_PITCH < REFERENCE_LINE_PITCH
    assert ARTICLE_SPEC.line_pitch == TIGHT_LINE_PITCH


def test_line_grid_scales_with_body_size() -> None:
    """本文サイズが違っても行送りの比率（約1.67行）が揃うこと。"""

    def ratio(spec: TemplateSpec) -> float:
        return spec.line_pitch / spec.body_size

    assert ratio(SHORT_SPEC) == pytest.approx(ratio(ARTICLE_SPEC), abs=0.05)


@pytest.mark.parametrize("spec", ALL_SPECS)
def test_section_properties_use_spec_line_pitch(spec: TemplateSpec) -> None:
    doc_grid = _find(build_section_properties(spec), "w:docGrid")
    assert _attr(doc_grid, "linePitch") == str(spec.line_pitch)


def test_char_grid_only_used_for_single_column_article() -> None:
    """字送りグリッドは 1 段幅前提のため、段組・行間変更時は外す。"""
    assert _attr(_find(build_section_properties(ARTICLE_SPEC), "w:docGrid"), "type") == (
        "linesAndChars"
    )
    for spec in (REVIEW_SPEC, SHORT_SPEC):
        assert _attr(_find(build_section_properties(spec), "w:docGrid"), "type") == "lines"


def test_apply_section_properties_keeps_footnote_settings_first() -> None:
    """`w:footnotePr` は `w:pgSz` より前に置く必要がある。"""
    root = ET.fromstring(apply_section_properties(_minimal_document_xml(), REVIEW_SPEC))
    assert [_tag(child) for child in _find(root, "w:body/w:sectPr")] == SECT_PR_ORDER


def test_apply_section_properties_replaces_single_sect_pr() -> None:
    root = ET.fromstring(apply_section_properties(_minimal_document_xml(), ARTICLE_SPEC))
    body = _find(root, "w:body")
    assert len(body.findall(f"{{{W_NS}}}sectPr")) == 1
    assert _tag(list(body)[-1]) == "sectPr"


# ============================================================
# apply_theme_fonts
# ============================================================


def test_apply_theme_fonts_separates_major_and_minor_japanese_faces() -> None:
    theme_xml = """<?xml version="1.0"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <a:themeElements>
    <a:fontScheme name="Office">
      <a:majorFont>
        <a:latin typeface="Arial"/>
        <a:font script="Jpan" typeface="ＭＳ ゴシック"/>
        <a:font script="Hans" typeface="宋体"/>
      </a:majorFont>
      <a:minorFont>
        <a:latin typeface="Century"/>
        <a:font script="Jpan" typeface="ＭＳ 明朝"/>
      </a:minorFont>
    </a:fontScheme>
  </a:themeElements>
</a:theme>""".encode()
    root = ET.fromstring(apply_theme_fonts(theme_xml))
    namespace = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

    def japanese(collection: str) -> str | None:
        parent = root.find(f".//{namespace}{collection}")
        assert parent is not None
        font = parent.find(f'{namespace}font[@script="Jpan"]')
        assert font is not None
        return font.get("typeface")

    assert japanese("majorFont") == HEADING_JA_FONT
    assert japanese("minorFont") == BODY_JA_FONT
    # 日本語以外のスクリプトは触らない
    chinese = [f for f in root.iter(f"{namespace}font") if f.get("script") == "Hans"]
    assert chinese[0].get("typeface") == "宋体"


# ============================================================
# build_template
# ============================================================


@pytest.mark.parametrize("spec", ALL_SPECS)
def test_build_template_returns_valid_docx(spec: TemplateSpec) -> None:
    with zipfile.ZipFile(io.BytesIO(build_template(_minimal_docx(), spec))) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {
            "word/styles.xml",
            "word/document.xml",
            "word/numbering.xml",
            "[Content_Types].xml",
        }
        for part in ("word/styles.xml", "word/document.xml", "word/numbering.xml"):
            ET.fromstring(archive.read(part))


def test_build_template_passes_through_untransformed_entries() -> None:
    with zipfile.ZipFile(io.BytesIO(build_template(_minimal_docx(), REVIEW_SPEC))) as archive:
        assert archive.read("[Content_Types].xml") == b"<Types/>"


@pytest.mark.parametrize("spec", ALL_SPECS)
def test_build_template_applies_spec_specific_layout(spec: TemplateSpec) -> None:
    with zipfile.ZipFile(io.BytesIO(build_template(_minimal_docx(), spec))) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))
        numbering = ET.fromstring(archive.read("word/numbering.xml"))

    sect_pr = _find(document, "w:body/w:sectPr")
    assert (sect_pr.find(f"{{{W_NS}}}lnNumType") is not None) is spec.line_numbers
    assert _attr(_find(sect_pr, "w:cols"), "num") == (
        str(spec.columns) if spec.columns > 1 else None
    )
    linked = [_attr(p, "val") for p in numbering.iter(f"{{{W_NS}}}pStyle")]
    assert len(linked) == spec.heading_depth
