"""Pandoc `--reference-doc` 用 Word テンプレートの生成。

`pandoc --print-default-data-file reference.docx` が出力する既定テンプレートを
ベースに、フォント・ページ設定・段落書式・見出しの自動採番を差し替えた
docx を組み立てる。

体裁は `templates/msword/ref/Graduation_paper_split.docx` で実際に使われている
スタイルに忠実に合わせている（テーマ参照を解決した実効値）。

    本文     Times New Roman + ＭＳ 明朝 12pt・両端揃え・字下げ 1 字
    見出し   Arial + ＭＳ ゴシック（1 章見出しのみ 14pt、以下 12pt）
    採番     第N章 / N.M. / N.M.K. をスタイル側で自動付番
    ページ   A4・余白 1440・行グリッド linePitch 466（テンプレートにより詰める）

ベースを Pandoc 既定テンプレートにしているのは、Pandoc が出力しうる
スタイル名（BodyText, FirstParagraph, ImageCaption, Bibliography 等）を
すべて含んでいるため。参考 docx を直接使うとこれらが未定義になり、
変換結果の大半が Word の既定書式にフォールバックしてしまう。
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, replace
from xml.etree import ElementTree as ET

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"

# --- フォント（参考 docx のテーマ参照を解決した実効値） ---
BODY_EN_FONT = "Times New Roman"
BODY_JA_FONT = "ＭＳ 明朝"
HEADING_EN_FONT = "Arial"
HEADING_JA_FONT = "ＭＳ ゴシック"
THEME_MINOR_EN_FONT = "Century"

# --- サイズ（half-point 単位。24 = 12pt） ---
#: 参考 docx の本文サイズ。1 段組はこれに合わせる。
BODY_SIZE = 24
#: 2 段組は 1 段が狭く、12pt では 1 行が 20 字を切って読みにくいため詰める。
COMPACT_BODY_SIZE = 21
TITLE_SIZE = 36
TOP_HEADING_SIZE = 28
SUB_HEADING_SIZE = 24
FOOTNOTE_SIZE = 18

# --- 長さ（twips 単位。1pt = 20twips, 1cm ≒ 567twips） ---
FIRST_LINE_INDENT = 227  # 全角 1 字ぶんの字下げ
HEADING_INDENT = 425  # 見出しのぶら下げ幅（採番と本文の間隔）
HEADING_SPACE = 280  # 章見出しの前後アキ
SUB_HEADING_SPACE = 120  # 節・項見出しの前後アキ

# --- 行送り（240 = 1.0 行） ---
SINGLE_LINE = 240
DOUBLE_LINE = 480

# --- ページ（A4 縦） ---
PAGE_WIDTH = 11900
PAGE_HEIGHT = 16840
#: 参考 docx は 1440（25.4mm）だが、12pt 本文だと 1 行 37 字しか入らず短い。
#: 20mm まで詰めて 1 行 40 字を確保する。
PAGE_MARGIN = 1134
HEADER_MARGIN = 851
FOOTER_MARGIN = 340
#: 段間。参考 docx の 720（12.7mm）は 2 段組には広すぎるので 7.5mm に詰める。
COLUMN_SPACE = 425

# --- 行グリッド（twips 単位の行送り） ---
#: 参考 docx の値。12pt 本文で約 1.94 行ぶんとかなり広い。
REFERENCE_LINE_PITCH = 466
#: 長文用に詰めたグリッド（12pt 本文で約 1.67 行）。
#: 参考 dotx `Word_Okugawa_template_Mac` と同値。
TIGHT_LINE_PITCH = 400
#: 2 段組用。10.5pt 本文で TIGHT_LINE_PITCH と同じ約 1.67 行になる。
COMPACT_LINE_PITCH = 350

# --- 見出しの自動採番 ---
# Pandoc 既定テンプレートは abstractNumId 990 / numId 1000 のみを使うため衝突しない。
HEADING_ABSTRACT_NUM_ID = "900"
HEADING_NUM_ID = "900"
#: 見出し階層ごとの採番書式とぶら下げインデント（参考 docx の numbering.xml より）。
HEADING_NUMBER_FORMATS = (
    ("第%1章", 425, 425),
    ("%1.%2.", 851, 426),
    ("%1.%2.%3.", 1276, 425),
    ("%4)", 1701, 425),
)
MAX_HEADING_LEVEL = 9


@dataclass(frozen=True)
class TemplateSpec:
    """1 つの Word テンプレートの構成。

    Attributes:
        filename: 出力ファイル名。
        label: 用途を表す短い説明（CLI 表示用）。
        columns: 段組数。
        heading_depth: 自動採番する見出しの階層数。これを超える階層は
            採番なしの簡易書式になる。
        page_break_before_chapter: 章見出しの前で改ページするか。
        body_line: 本文の行送り（240 = 1.0 行）。None なら行グリッドに従う。
        line_numbers: 行番号を振るか（校閲時の指摘位置の特定用）。
        char_grid: 字送りグリッドを使うか。段組時は 1 段幅を前提とした
            字送りが崩れるため False にする。
        line_pitch: 行グリッドの行送り（twips）。`body_line` を指定した
            場合はグリッドに吸着させないため使われない。
        body_size: 本文の文字サイズ（half-point）。
    """

    filename: str
    label: str
    columns: int
    heading_depth: int
    page_break_before_chapter: bool
    body_line: int | None
    line_numbers: bool
    char_grid: bool
    line_pitch: int
    body_size: int = BODY_SIZE


#: 長文の article 形式。章・節・項・小項目の 4 階層を採番する。
#: 分量が出るため行グリッドは参考 docx より詰める。
ARTICLE_SPEC = TemplateSpec(
    filename="template-article.docx",
    label="1段組・章節項の4階層・章ごとに改ページ",
    columns=1,
    heading_depth=4,
    page_break_before_chapter=True,
    body_line=None,
    line_numbers=False,
    char_grid=True,
    line_pitch=TIGHT_LINE_PITCH,
)

#: 校閲用。1 段組・行間 2 行・章見出しのみ（節以下は採番しない）。
REVIEW_SPEC = TemplateSpec(
    filename="template-review.docx",
    label="1段組・行間2行・章見出しのみ・行番号あり",
    columns=1,
    heading_depth=1,
    page_break_before_chapter=True,
    body_line=DOUBLE_LINE,
    line_numbers=True,
    char_grid=False,
    line_pitch=REFERENCE_LINE_PITCH,
)

#: ショートペーパー。2 段組・章と節の 2 階層まで・改ページなし。
#: 1 段が狭いので本文は 10.5pt に詰める。
SHORT_SPEC = TemplateSpec(
    filename="template-short.docx",
    label="2段組・10.5pt・章節の2階層・改ページなし",
    columns=2,
    heading_depth=2,
    page_break_before_chapter=False,
    body_line=None,
    line_numbers=False,
    char_grid=False,
    line_pitch=COMPACT_LINE_PITCH,
    body_size=COMPACT_BODY_SIZE,
)

ALL_SPECS = (ARTICLE_SPEC, REVIEW_SPEC, SHORT_SPEC)


@dataclass(frozen=True)
class ParagraphFormat:
    """段落書式（`w:pPr` に対応）。None の項目は出力しない。"""

    keep_next: bool = False
    keep_lines: bool = False
    page_break_before: bool = False
    widow_control_off: bool = False
    numbering_level: int | None = None
    snap_to_grid: bool | None = None
    space_before: int | None = None
    space_after: int | None = None
    line: int | None = None
    indent_left: int | None = None
    indent_right: int | None = None
    indent_hanging: int | None = None
    indent_first_line: int | None = None
    justification: str | None = None
    outline_level: int | None = None


@dataclass(frozen=True)
class RunFormat:
    """文字書式（`w:rPr` に対応）。None の項目は出力しない。"""

    bold: bool = False
    size: int | None = None
    color: str | None = None
    heading_fonts: bool = False
    body_fonts: bool = False


@dataclass(frozen=True)
class StyleOverride:
    """既定テンプレートのスタイル定義を上書きする内容。"""

    paragraph: ParagraphFormat | None = None
    run: RunFormat | None = None


def _q(tag: str, ns: str = W_NS) -> str:
    """`w:pPr` のような接頭辞つきタグを ElementTree の完全修飾名に変換する。"""
    return f"{{{ns}}}{tag}"


def _serialize(root: ET.Element) -> bytes:
    """XML ツリーを宣言つき UTF-8 バイト列へ書き出す。"""
    xml: bytes = ET.tostring(root, encoding="UTF-8", xml_declaration=True)
    return xml


def _sub(parent: ET.Element, tag: str, **attrib: str) -> ET.Element:
    """`w:` 名前空間の子要素を、属性名も `w:` 修飾したうえで追加する。"""
    element = ET.SubElement(parent, _q(tag))
    for key, value in attrib.items():
        element.set(_q(key), value)
    return element


def _font_element(parent: ET.Element, *, heading: bool) -> ET.Element:
    """和文 / 欧文フォントを明示指定した `w:rFonts` を追加する。

    参考 docx はテーマ参照（`majorEastAsia` 等）でフォントを解決しているが、
    テーマの異なる環境で開いてもフォントが変わらないよう実名で書き出す。
    解決後の値は参考 docx と同一。
    """
    latin = HEADING_EN_FONT if heading else BODY_EN_FONT
    japanese = HEADING_JA_FONT if heading else BODY_JA_FONT
    return _sub(parent, "rFonts", ascii=latin, eastAsia=japanese, hAnsi=latin, cs=BODY_EN_FONT)


def build_paragraph_properties(fmt: ParagraphFormat) -> ET.Element:
    """`ParagraphFormat` から `w:pPr` 要素を組み立てる。

    子要素は OOXML の `CT_PPrBase` が定めるスキーマ順で出力する
    （順序が違うと Word がファイルを破損扱いにする）。
    """
    p_pr = ET.Element(_q("pPr"))
    if fmt.keep_next:
        _sub(p_pr, "keepNext")
    if fmt.keep_lines:
        _sub(p_pr, "keepLines")
    if fmt.page_break_before:
        _sub(p_pr, "pageBreakBefore")
    if fmt.widow_control_off:
        _sub(p_pr, "widowControl", val="0")
    if fmt.numbering_level is not None:
        num_pr = _sub(p_pr, "numPr")
        _sub(num_pr, "ilvl", val=str(fmt.numbering_level))
        _sub(num_pr, "numId", val=HEADING_NUM_ID)
    if fmt.snap_to_grid is not None:
        _sub(p_pr, "snapToGrid", val="1" if fmt.snap_to_grid else "0")

    spacing: dict[str, str] = {}
    if fmt.space_before is not None:
        spacing["before"] = str(fmt.space_before)
    if fmt.space_after is not None:
        spacing["after"] = str(fmt.space_after)
    if fmt.line is not None:
        spacing["line"] = str(fmt.line)
        spacing["lineRule"] = "auto"
    if spacing:
        _sub(p_pr, "spacing", **spacing)

    indent: dict[str, str] = {}
    if fmt.indent_left is not None:
        indent["left"] = str(fmt.indent_left)
    if fmt.indent_right is not None:
        indent["right"] = str(fmt.indent_right)
    if fmt.indent_hanging is not None:
        indent["hanging"] = str(fmt.indent_hanging)
    if fmt.indent_first_line is not None:
        indent["firstLine"] = str(fmt.indent_first_line)
    if indent:
        _sub(p_pr, "ind", **indent)

    if fmt.justification is not None:
        _sub(p_pr, "jc", val=fmt.justification)
    if fmt.outline_level is not None:
        _sub(p_pr, "outlineLvl", val=str(fmt.outline_level))
    return p_pr


def build_run_properties(fmt: RunFormat) -> ET.Element:
    """`RunFormat` から `w:rPr` 要素を組み立てる（`CT_RPr` のスキーマ順）。"""
    r_pr = ET.Element(_q("rPr"))
    if fmt.heading_fonts or fmt.body_fonts:
        _font_element(r_pr, heading=fmt.heading_fonts)
    if fmt.bold:
        _sub(r_pr, "b")
        _sub(r_pr, "bCs")
    if fmt.color is not None:
        _sub(r_pr, "color", val=fmt.color)
    if fmt.size is not None:
        _sub(r_pr, "sz", val=str(fmt.size))
        _sub(r_pr, "szCs", val=str(fmt.size))
    return r_pr


def build_heading_override(spec: TemplateSpec, level: int) -> StyleOverride:
    """見出し 1 階層ぶんのスタイル上書きを組み立てる。

    `spec.heading_depth` を超える階層は、参考 docx の `4_見出し` と同様に
    採番もインデントも持たない簡易な見出しにする。ただし本文と区別が
    つくよう見出しフォントは維持する。

    Args:
        spec: 対象テンプレートの構成。
        level: 見出しの階層（1 始まり）。

    Returns:
        `HeadingN` スタイルの上書き定義。
    """
    if level > spec.heading_depth:
        return StyleOverride(
            paragraph=ParagraphFormat(
                keep_next=True,
                widow_control_off=True,
                space_before=SUB_HEADING_SPACE,
                space_after=SUB_HEADING_SPACE,
                indent_first_line=0,
                justification="left",
                outline_level=level - 1,
            ),
            run=RunFormat(size=SUB_HEADING_SIZE, color="000000", heading_fonts=True),
        )

    is_chapter = level == 1
    paragraph = ParagraphFormat(
        keep_next=True,
        page_break_before=is_chapter and spec.page_break_before_chapter,
        widow_control_off=True,
        numbering_level=level - 1,
        space_before=HEADING_SPACE if is_chapter else SUB_HEADING_SPACE,
        space_after=HEADING_SPACE if is_chapter else SUB_HEADING_SPACE,
        justification="left",
        outline_level=level - 1,
    )
    # 章見出しのインデントは採番定義側に持たせる（参考 docx の 1_見出し に同じ）。
    if level == 2:
        paragraph = replace(paragraph, indent_left=HEADING_INDENT, indent_hanging=HEADING_INDENT)
    elif level == 3:
        paragraph = replace(paragraph, indent_left=HEADING_INDENT)

    return StyleOverride(
        paragraph=paragraph,
        run=RunFormat(
            size=TOP_HEADING_SIZE if is_chapter else SUB_HEADING_SIZE,
            color="000000",
            heading_fonts=True,
        ),
    )


def build_style_overrides(spec: TemplateSpec) -> dict[str, StyleOverride]:
    """テンプレート構成に応じたスタイル上書き定義を返す。

    Args:
        spec: 対象テンプレートの構成。

    Returns:
        `w:styleId` をキーとした上書き定義。
    """
    # 参考 docx の Normal（widowControl 無効・両端揃え・欧文 Times New Roman）。
    normal = ParagraphFormat(
        widow_control_off=True,
        snap_to_grid=spec.char_grid if spec.body_line is not None else None,
        line=spec.body_line,
        justification="both",
    )
    # `1_本文` = Normal + 全角 1 字の字下げ。
    body = replace(normal, indent_first_line=FIRST_LINE_INDENT)
    # `1_Caption` / `1_citation` = Normal のみ（字下げしない）。
    plain = replace(normal, indent_first_line=0)

    overrides: dict[str, StyleOverride] = {
        "Normal": StyleOverride(
            paragraph=normal,
            run=RunFormat(size=spec.body_size, body_fonts=True),
        ),
        "BodyText": StyleOverride(paragraph=body),
        # 日本語組版では見出し直後の段落も字下げするため本文と同一。
        "FirstParagraph": StyleOverride(paragraph=body),
        "Compact": StyleOverride(paragraph=plain),
        "Caption": StyleOverride(paragraph=plain),
        "Bibliography": StyleOverride(paragraph=plain),
        "BlockText": StyleOverride(
            paragraph=replace(plain, indent_left=HEADING_INDENT, indent_right=HEADING_INDENT)
        ),
        # `1_Figure` = Normal + keepNext + 中央揃え。
        "Figure": StyleOverride(paragraph=replace(plain, keep_next=True, justification="center")),
        "CaptionedFigure": StyleOverride(
            paragraph=replace(plain, keep_next=True, justification="center")
        ),
        # 参考 docx の Subtitle（18pt・中央揃え）を表題に充てる。
        "Title": StyleOverride(
            paragraph=replace(
                plain, keep_next=True, space_after=HEADING_SPACE, justification="center"
            ),
            run=RunFormat(size=TITLE_SIZE, color="000000", body_fonts=True),
        ),
        "Subtitle": StyleOverride(
            paragraph=replace(
                plain, keep_next=True, space_after=SUB_HEADING_SPACE, justification="center"
            ),
            run=RunFormat(size=TOP_HEADING_SIZE, color="000000", body_fonts=True),
        ),
        "Author": StyleOverride(
            paragraph=replace(
                plain, keep_next=True, space_after=SUB_HEADING_SPACE, justification="center"
            ),
            run=RunFormat(size=spec.body_size, color="000000", body_fonts=True),
        ),
        "Date": StyleOverride(
            paragraph=replace(plain, space_after=HEADING_SPACE, justification="center"),
            run=RunFormat(size=spec.body_size, color="000000", body_fonts=True),
        ),
        # 参考 docx の `0_見出し`（採番なし・中央揃え・明朝・太字）に対応。
        "AbstractTitle": StyleOverride(
            paragraph=replace(
                plain,
                keep_next=True,
                space_before=HEADING_SPACE,
                space_after=HEADING_SPACE,
                justification="center",
            ),
            run=RunFormat(bold=True, size=TOP_HEADING_SIZE, color="000000", body_fonts=True),
        ),
        "Abstract": StyleOverride(paragraph=body),
        "FootnoteText": StyleOverride(
            paragraph=replace(plain, line=SINGLE_LINE, snap_to_grid=False),
            run=RunFormat(size=FOOTNOTE_SIZE, body_fonts=True),
        ),
    }

    for level in range(1, MAX_HEADING_LEVEL + 1):
        overrides[f"Heading{level}"] = build_heading_override(spec, level)

    # TableCaption / ImageCaption は Caption を継承するので個別指定は不要。
    return overrides


def _replace_child(style: ET.Element, new_child: ET.Element) -> None:
    """`w:style` 配下の `w:pPr` / `w:rPr` を差し替える。

    `w:style` の子要素順は「メタ情報 → pPr → rPr」と決まっており、
    メタ情報のみが残った状態への追記は常に末尾で正しい順序になる。
    """
    existing = style.find(new_child.tag)
    if existing is not None:
        style.remove(existing)
    style.append(new_child)


def apply_style_overrides(styles_xml: bytes, spec: TemplateSpec) -> bytes:
    """`word/styles.xml` にフォント・段落書式の上書きを適用する。

    Args:
        styles_xml: Pandoc 既定テンプレートの styles.xml。
        spec: 対象テンプレートの構成。

    Returns:
        書き換え後の XML バイト列。
    """
    ET.register_namespace("w", W_NS)
    root = ET.fromstring(styles_xml)

    _apply_doc_defaults(root, spec)

    overrides = build_style_overrides(spec)
    for style in root.findall(_q("style")):
        style_id = style.get(_q("styleId"))
        override = overrides.get(style_id or "")
        if override is None:
            continue
        if override.paragraph is not None:
            _replace_child(style, build_paragraph_properties(override.paragraph))
        if override.run is not None:
            _replace_child(style, build_run_properties(override.run))

    return _serialize(root)


def _apply_doc_defaults(root: ET.Element, spec: TemplateSpec) -> None:
    """`w:docDefaults` の既定フォント・サイズ・言語を差し替える。"""
    doc_defaults = root.find(_q("docDefaults"))
    if doc_defaults is None:
        return

    r_pr_default = doc_defaults.find(_q("rPrDefault"))
    if r_pr_default is not None:
        for existing in r_pr_default.findall(_q("rPr")):
            r_pr_default.remove(existing)
        r_pr = ET.SubElement(r_pr_default, _q("rPr"))
        _font_element(r_pr, heading=False)
        _sub(r_pr, "kern", val="2")
        _sub(r_pr, "sz", val=str(spec.body_size))
        _sub(r_pr, "szCs", val=str(spec.body_size))
        _sub(r_pr, "lang", val="en-AU", eastAsia="ja-JP", bidi="ar-SA")

    p_pr_default = doc_defaults.find(_q("pPrDefault"))
    if p_pr_default is not None:
        # Pandoc 既定の「段落後 200」が残ると行送り指定と二重にかかる。
        for existing in p_pr_default.findall(_q("pPr")):
            p_pr_default.remove(existing)
        p_pr = ET.SubElement(p_pr_default, _q("pPr"))
        _sub(p_pr, "spacing", before="0", after="0")


def build_heading_numbering(spec: TemplateSpec) -> tuple[ET.Element, ET.Element]:
    """見出しの自動採番定義（`w:abstractNum` と `w:num`）を組み立てる。

    参考 docx と同じく採番をスタイル側に持たせるため、各階層に
    `w:pStyle` で `HeadingN` を結びつける。`spec.heading_depth` を
    超える階層には結びつけないので、その階層は採番されない。

    Args:
        spec: 対象テンプレートの構成。

    Returns:
        `(w:abstractNum, w:num)` の組。
    """
    abstract_num = ET.Element(_q("abstractNum"))
    abstract_num.set(_q("abstractNumId"), HEADING_ABSTRACT_NUM_ID)
    _sub(abstract_num, "nsid", val="46334313")
    _sub(abstract_num, "multiLevelType", val="multilevel")

    for index, (text, left, hanging) in enumerate(HEADING_NUMBER_FORMATS):
        level = _sub(abstract_num, "lvl", ilvl=str(index))
        _sub(level, "start", val="1")
        _sub(level, "numFmt", val="decimal" if index < 3 else "lowerLetter")
        if index < spec.heading_depth:
            _sub(level, "pStyle", val=f"Heading{index + 1}")
        _sub(level, "lvlText", val=text)
        _sub(level, "lvlJc", val="left")
        level_p_pr = _sub(level, "pPr")
        _sub(level_p_pr, "ind", left=str(left), hanging=str(hanging))

    num = ET.Element(_q("num"))
    num.set(_q("numId"), HEADING_NUM_ID)
    _sub(num, "abstractNumId", val=HEADING_ABSTRACT_NUM_ID)
    return abstract_num, num


def apply_heading_numbering(numbering_xml: bytes, spec: TemplateSpec) -> bytes:
    """`word/numbering.xml` に見出しの採番定義を追加する。

    `CT_Numbering` は「すべての `w:abstractNum` → すべての `w:num`」の順を
    要求するため、`w:abstractNum` は最後の同種要素の直後に挿入する。
    """
    ET.register_namespace("w", W_NS)
    root = ET.fromstring(numbering_xml)
    abstract_num, num = build_heading_numbering(spec)

    children = list(root)
    last_abstract = max(
        (index for index, child in enumerate(children) if child.tag == _q("abstractNum")),
        default=-1,
    )
    root.insert(last_abstract + 1, abstract_num)
    root.append(num)
    return _serialize(root)


def build_section_properties(spec: TemplateSpec) -> ET.Element:
    """ページサイズ・余白・段組を定めた `w:sectPr` を組み立てる。

    子要素は `CT_SectPr` のスキーマ順（pgSz → pgMar → lnNumType → cols → docGrid）。
    """
    sect_pr = ET.Element(_q("sectPr"))
    _sub(sect_pr, "pgSz", w=str(PAGE_WIDTH), h=str(PAGE_HEIGHT), code="9")
    _sub(
        sect_pr,
        "pgMar",
        top=str(PAGE_MARGIN),
        right=str(PAGE_MARGIN),
        bottom=str(PAGE_MARGIN),
        left=str(PAGE_MARGIN),
        header=str(HEADER_MARGIN),
        footer=str(FOOTER_MARGIN),
        gutter="0",
    )
    if spec.line_numbers:
        _sub(sect_pr, "lnNumType", countBy="1", restart="continuous")
    if spec.columns > 1:
        _sub(sect_pr, "cols", num=str(spec.columns), space=str(COLUMN_SPACE), equalWidth="1")
    else:
        _sub(sect_pr, "cols", space=str(COLUMN_SPACE))
    grid_type = "linesAndChars" if spec.char_grid else "lines"
    _sub(sect_pr, "docGrid", type=grid_type, linePitch=str(spec.line_pitch))
    return sect_pr


def apply_section_properties(document_xml: bytes, spec: TemplateSpec) -> bytes:
    """`word/document.xml` の `w:sectPr` をページ設定つきのものへ差し替える。

    Pandoc の既定テンプレートの `w:sectPr` には脚注設定しか入っておらず、
    ページサイズも段組も未指定のため Word の既定値が使われてしまう。
    既存の子要素（`w:footnotePr` 等）は先頭に残す。
    """
    ET.register_namespace("w", W_NS)
    root = ET.fromstring(document_xml)
    body = root.find(_q("body"))
    if body is None:
        return document_xml

    new_sect_pr = build_section_properties(spec)
    old_sect_pr = body.find(_q("sectPr"))
    if old_sect_pr is not None:
        # footnotePr / endnotePr は pgSz より前に来る必要がある。
        for index, child in enumerate(list(old_sect_pr)):
            new_sect_pr.insert(index, child)
        body.remove(old_sect_pr)
    body.append(new_sect_pr)

    return _serialize(root)


def apply_theme_fonts(theme_xml: bytes) -> bytes:
    """テーマの見出し用 / 本文用フォントを参考 docx と同じ構成に揃える。

    スタイル側では実フォント名を明示しているが、テンプレートを Word で
    直接編集したときにテーマ由来のフォントが混ざらないようにする。
    """
    ET.register_namespace("a", A_NS)
    root = ET.fromstring(theme_xml)
    faces = {
        "majorFont": (HEADING_EN_FONT, HEADING_JA_FONT),
        "minorFont": (THEME_MINOR_EN_FONT, BODY_JA_FONT),
    }
    for scheme in root.iter(f"{{{A_NS}}}fontScheme"):
        for collection, (latin_face, japanese_face) in faces.items():
            font_collection = scheme.find(f"{{{A_NS}}}{collection}")
            if font_collection is None:
                continue
            latin = font_collection.find(f"{{{A_NS}}}latin")
            if latin is not None:
                latin.set("typeface", latin_face)
            for font in font_collection.findall(f"{{{A_NS}}}font"):
                if font.get("script") == "Jpan":
                    font.set("typeface", japanese_face)
    return _serialize(root)


def build_template(base_docx: bytes, spec: TemplateSpec) -> bytes:
    """ベース docx から Word テンプレートを組み立てる。

    Args:
        base_docx: `pandoc --print-default-data-file reference.docx` の出力。
        spec: 対象テンプレートの構成。

    Returns:
        書き換え後の docx バイト列。
    """
    transforms = {
        "word/styles.xml": lambda data: apply_style_overrides(data, spec),
        "word/document.xml": lambda data: apply_section_properties(data, spec),
        "word/numbering.xml": lambda data: apply_heading_numbering(data, spec),
        "word/theme/theme1.xml": apply_theme_fonts,
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(base_docx)) as source:
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as target:
            for item in source.infolist():
                data = source.read(item.filename)
                transform = transforms.get(item.filename)
                if transform is not None:
                    data = transform(data)
                target.writestr(item, data)
    return buffer.getvalue()
