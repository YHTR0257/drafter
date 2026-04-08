"""tests/drafter/reviewer/test_splitter.py

reviewer/splitter.py のミラーテスト。
"""

from pathlib import Path


from drafter.common.tex_parser import Document, Section, TexParser
from drafter.reviewer.splitter import Chunk, Splitter


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def make_document(raw: str, sections: list[Section] | None = None) -> Document:
    return Document(
        root_path=Path("/fake/main.tex"),
        raw_content=raw,
        sections=sections or [],
    )


def make_section(
    title: str,
    content: str,
    level: str = "section",
    children: list[Section] | None = None,
) -> Section:
    return Section(level=level, title=title, content=content, children=children or [])


def splitter(max_tokens: int = 10_000) -> Splitter:
    return Splitter(max_tokens=max_tokens, parser=TexParser())


# ---------------------------------------------------------------------------
# Chunk データクラス
# ---------------------------------------------------------------------------


class TestChunk:
    def test_fields(self) -> None:
        c = Chunk(label="intro", content="text", token_estimate=5)
        assert c.label == "intro"
        assert c.content == "text"
        assert c.token_estimate == 5


# ---------------------------------------------------------------------------
# split - 文書全体が収まる場合
# ---------------------------------------------------------------------------


class TestSplitWholeDocument:
    def test_small_doc_returns_single_chunk(self) -> None:
        doc = make_document("short text")
        chunks = splitter(max_tokens=10_000).split(doc)
        assert len(chunks) == 1
        assert chunks[0].label == "whole"

    def test_chunk_contains_full_content(self) -> None:
        doc = make_document("hello world")
        chunks = splitter(max_tokens=10_000).split(doc)
        assert chunks[0].content == "hello world"

    def test_token_estimate_set(self) -> None:
        doc = make_document("a" * 200)
        chunks = splitter(max_tokens=10_000).split(doc)
        assert chunks[0].token_estimate > 0


# ---------------------------------------------------------------------------
# split - セクション単位に分割
# ---------------------------------------------------------------------------


class TestSplitBySections:
    def test_splits_into_section_chunks(self) -> None:
        intro = make_section("intro", "A" * 100)
        method = make_section("method", "B" * 100)
        raw = "A" * 100 + "B" * 100
        doc = make_document(raw, sections=[intro, method])

        # max_tokens を小さくして強制分割
        chunks = splitter(max_tokens=50).split(doc)
        labels = [c.label for c in chunks]
        assert any("intro" in label for label in labels)
        assert any("method" in label for label in labels)

    def test_label_includes_section_title(self) -> None:
        sec = make_section("結果", "content")
        doc = make_document("content", sections=[sec])
        chunks = splitter(max_tokens=1).split(doc)
        assert any("結果" in chunk.label for chunk in chunks)

    def test_child_section_label_is_nested(self) -> None:
        child = make_section("実験手法", "detail", level="subsection")
        parent = make_section("method", "intro\n", children=[child])
        doc = make_document("intro\ndetail", sections=[parent])
        chunks = splitter(max_tokens=1).split(doc)
        labels = [c.label for c in chunks]
        assert any("実験手法" in label for label in labels)


# ---------------------------------------------------------------------------
# _force_split - 行単位での強制分割
# ---------------------------------------------------------------------------


class TestForceSplit:
    def test_large_content_split_into_multiple_chunks(self) -> None:
        # 1行 = 100文字 → token = 50。max_tokens=60 なら1行ずつ分割
        line = "A" * 100 + "\n"
        sec = make_section("big", line * 5)
        doc = make_document(line * 5, sections=[sec])
        chunks = splitter(max_tokens=60).split(doc)
        assert len(chunks) > 1

    def test_part_suffix_added_when_multiple_chunks(self) -> None:
        line = "A" * 100 + "\n"
        sec = make_section("big", line * 4)
        doc = make_document(line * 4, sections=[sec])
        chunks = splitter(max_tokens=60).split(doc)
        # [1], [2], ... サフィックスが付く
        assert any("[1]" in c.label for c in chunks)

    def test_no_suffix_for_single_chunk(self) -> None:
        doc = make_document("short")
        chunks = splitter(max_tokens=10_000).split(doc)
        assert "[1]" not in chunks[0].label
