"""LaTeX文書をコンテキスト長に収まるチャンクへ分割する。

分割戦略（段階的細分化）:
    1. 文書全体が max_tokens に収まる → 1チャンクで返す
    2. 収まらない → トップレベルセクション単位に分割
    3. セクションが収まらない → subsection 単位に細分化
    4. それでも収まらない → テキストを行単位で強制分割
"""

from __future__ import annotations

from dataclasses import dataclass

from drafter.common.tex_parser import Document, Section, TexParser


@dataclass
class Chunk:
    """レビューの1単位。"""

    label: str  # 例: "introduction", "method > 実験手法"
    content: str  # raw LaTeXテキスト
    token_estimate: int


class Splitter:
    """Document をチャンク列に分割するクラス。"""

    def __init__(self, max_tokens: int, parser: TexParser) -> None:
        self._max = max_tokens
        self._parser = parser

    def split(self, document: Document) -> list[Chunk]:
        """文書をチャンク列に変換する。"""
        whole = document.raw_content
        if self._parser.estimate_tokens(whole) <= self._max:
            return [
                Chunk(
                    label="whole",
                    content=whole,
                    token_estimate=self._parser.estimate_tokens(whole),
                )
            ]

        chunks: list[Chunk] = []
        for sec in document.sections:
            chunks.extend(self._split_section(sec, parent_label=""))
        return chunks

    # ------------------------------------------------------------------

    def _split_section(self, sec: Section, parent_label: str) -> list[Chunk]:
        label = f"{parent_label} > {sec.title}".lstrip(" > ")
        content = self._section_full_content(sec)

        if self._parser.estimate_tokens(content) <= self._max:
            return [
                Chunk(
                    label=label,
                    content=content,
                    token_estimate=self._parser.estimate_tokens(content),
                )
            ]

        # 子セクションがあれば細分化
        if sec.children:
            chunks: list[Chunk] = []
            # 直下コンテンツ（子セクション本文を除いた部分）
            if sec.content.strip():
                chunks.extend(self._force_split(label, sec.content))
            for child in sec.children:
                chunks.extend(self._split_section(child, label))
            return chunks

        # 子セクションがなければ行単位で強制分割
        return self._force_split(label, content)

    def _section_full_content(self, sec: Section) -> str:
        """セクションの全テキスト（子セクション込み）を返す。"""
        parts = [f"\\{sec.level}{{{sec.title}}}\n", sec.content]
        for child in sec.children:
            parts.append(self._section_full_content(child))
        return "".join(parts)

    def _force_split(self, label: str, content: str) -> list[Chunk]:
        """テキストを行単位で max_tokens 以内に強制分割する。"""
        lines = content.splitlines(keepends=True)
        chunks: list[Chunk] = []
        buf: list[str] = []
        buf_tokens = 0
        part = 1

        for line in lines:
            line_tokens = self._parser.estimate_tokens(line)
            if buf and buf_tokens + line_tokens > self._max:
                text = "".join(buf)
                chunks.append(
                    Chunk(
                        label=f"{label} [{part}]",
                        content=text,
                        token_estimate=buf_tokens,
                    )
                )
                part += 1
                buf = []
                buf_tokens = 0
            buf.append(line)
            buf_tokens += line_tokens

        if buf:
            text = "".join(buf)
            suffix = f" [{part}]" if part > 1 else ""
            chunks.append(
                Chunk(
                    label=f"{label}{suffix}",
                    content=text,
                    token_estimate=buf_tokens,
                )
            )

        return chunks
