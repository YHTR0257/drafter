"""LaTeX文書のパーサー。

\\input{} の再帰展開、セクション階層の抽出、数式・環境の識別、
トークン長の推定を提供する。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Environment:
    """LaTeX環境（equation, figure, table など）。"""

    name: str
    content: str
    line_start: int
    line_end: int


@dataclass
class Section:
    """chapter / section / subsection / subsubsection の一階層。"""

    level: str  # "chapter" | "section" | "subsection" | "subsubsection"
    title: str
    content: str  # この階層直下のテキスト（子セクションを除く）
    children: list[Section] = field(default_factory=list)
    environments: list[Environment] = field(default_factory=list)


@dataclass
class Document:
    """パース済み文書。"""

    root_path: Path
    raw_content: str  # \\input{} 展開済みの全文
    sections: list[Section] = field(default_factory=list)


# セクションコマンドの順序（広い → 狭い）
_SECTION_LEVELS = ["chapter", "section", "subsection", "subsubsection"]

# 認識する環境名
_ENV_NAMES: frozenset[str] = frozenset(
    {
        "equation",
        "equation*",
        "align",
        "align*",
        "gather",
        "gather*",
        "multline",
        "multline*",
        "figure",
        "figure*",
        "table",
        "table*",
        "itemize",
        "enumerate",
        "description",
        "tabular",
    }
)

# \\input{...} または \\input{...} (拡張子なし可) にマッチ
_INPUT_RE = re.compile(r"\\input\{([^}]+)\}")

# \\section{...} 等にマッチ（レベル名 → タイトル）
_SECTION_RE = re.compile(r"\\(chapter|section|subsection|subsubsection)\{([^}]*)\}")

# \\begin{name} / \\end{name}
_BEGIN_RE = re.compile(r"\\begin\{([^}]+)\}")
_END_RE = re.compile(r"\\end\{([^}]+)\}")


class TexParser:
    """LaTeX文書のパーサー。"""

    def resolve_inputs(self, path: Path) -> str:
        """\\input{} を再帰的に展開して全文を返す。"""
        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return f"% [ERROR: file not found: {path}]\n"

        def replace_input(m: re.Match[str]) -> str:
            ref = m.group(1).strip()
            ref_path = path.parent / ref
            if not ref_path.suffix:
                ref_path = ref_path.with_suffix(".tex")
            return self.resolve_inputs(ref_path)

        return _INPUT_RE.sub(replace_input, content)

    def parse(self, path: Path) -> Document:
        """path を起点にLaTeX文書をパースし Document を返す。"""
        raw = self.resolve_inputs(path)
        sections = self._extract_sections(raw)
        return Document(root_path=path, raw_content=raw, sections=sections)

    def estimate_tokens(self, text: str) -> int:
        """テキストのトークン数を保守的に推定する。

        日英混在テキストを想定し ``len(text) // 2`` で近似する。
        日本語1文字 ≈ 1 token、英語4文字 ≈ 1 token の中間値。
        """
        return max(1, len(text) // 2)

    # ------------------------------------------------------------------
    # 内部実装
    # ------------------------------------------------------------------

    def _extract_sections(self, content: str) -> list[Section]:
        """トップレベルのセクションリストを抽出する。

        文書内で実際に使われている最上位のセクションレベルを自動検出する。
        chapter があれば chapter を起点に、なければ section を起点にする。
        """
        lines = content.splitlines(keepends=True)
        tokens = self._tokenize(lines)

        used_levels = {str(tok["level"]) for tok in tokens if tok["type"] == "section"}
        if not used_levels:
            return []

        start_idx = min(_SECTION_LEVELS.index(lv) for lv in used_levels if lv in _SECTION_LEVELS)
        return self._build_tree(tokens, level_idx=start_idx)

    def _tokenize(self, lines: list[str]) -> list[dict[str, object]]:
        """行リストをセクション境界・テキスト・環境のトークン列に変換する。"""
        tokens: list[dict[str, object]] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            m_sec = _SECTION_RE.search(line)
            if m_sec:
                tokens.append(
                    {
                        "type": "section",
                        "level": m_sec.group(1),
                        "title": m_sec.group(2),
                        "line": i,
                    }
                )
                i += 1
                continue

            m_begin = _BEGIN_RE.search(line)
            if m_begin and m_begin.group(1) in _ENV_NAMES:
                env_name = m_begin.group(1)
                env_lines = [line]
                start_line = i
                i += 1
                depth = 1
                while i < len(lines) and depth > 0:
                    env_lines.append(lines[i])
                    if _BEGIN_RE.search(lines[i]):
                        depth += 1
                    m_end = _END_RE.search(lines[i])
                    if m_end and m_end.group(1) == env_name.rstrip("*"):
                        depth -= 1
                        if depth == 0:
                            i += 1
                            break
                    i += 1
                tokens.append(
                    {
                        "type": "env",
                        "name": env_name,
                        "content": "".join(env_lines),
                        "line_start": start_line,
                        "line_end": i - 1,
                    }
                )
                continue

            tokens.append({"type": "text", "content": line, "line": i})
            i += 1
        return tokens

    def _build_tree(self, tokens: list[dict[str, object]], level_idx: int) -> list[Section]:
        """トークン列を再帰的にセクションツリーへ変換する。"""
        if level_idx >= len(_SECTION_LEVELS):
            return []

        sections: list[Section] = []
        current: Section | None = None
        pending_content: list[str] = []
        pending_envs: list[Environment] = []

        def flush_pending() -> None:
            nonlocal pending_content, pending_envs
            if current is not None:
                current.content += "".join(pending_content)
                current.environments.extend(pending_envs)
            pending_content = []
            pending_envs = []

        for tok in tokens:
            tok_type = tok["type"]

            if tok_type == "section":
                level = str(tok["level"])
                title = str(tok["title"])
                tok_level_idx = _SECTION_LEVELS.index(level)

                if tok_level_idx == level_idx:
                    flush_pending()
                    current = Section(level=level, title=title, content="")
                    sections.append(current)
                elif tok_level_idx > level_idx:
                    # 子セクションは後でまとめて処理する（pending に残す）
                    pending_content.append(f"\\{level}{{{title}}}\n")
                else:
                    # 上位レベルは呼び出し元が処理する
                    pending_content.append(f"\\{level}{{{title}}}\n")

            elif tok_type == "env":
                env = Environment(
                    name=str(tok["name"]),
                    content=str(tok["content"]),
                    line_start=int(str(tok["line_start"])),
                    line_end=int(str(tok["line_end"])),
                )
                if current is not None:
                    pending_envs.append(env)
                # current がない場合は無視（プリアンブル等）

            else:  # text
                pending_content.append(str(tok["content"]))

        flush_pending()

        # 各セクションの子を再帰的に抽出
        for sec in sections:
            sec.children = self._build_tree(
                self._tokenize(sec.content.splitlines(keepends=True)),
                level_idx + 1,
            )

        return sections
