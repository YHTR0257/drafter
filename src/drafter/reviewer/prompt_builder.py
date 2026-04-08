"""レビュープロンプトの構築。

チャンク + ルールファイル + 共通出力指示を組み合わせて
OpenAI messages 形式のプロンプトを生成する。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from drafter.reviewer.splitter import Chunk

SYSTEM_PROMPT = """\
あなたは学術論文のレビュアーです。
提示されたLaTeXテキストを読み、以下の観点から日本語でコメントしてください。

出力フォーマット:
- 問題点は箇条書きで記述してください。
- 各項目には「[重要度: 高/中/低]」を付けてください。
- 問題がない場合は「問題なし」と記述してください。
- 修正案がある場合は具体的に示してください。
"""

_OUTPUT_INSTRUCTION = """\

---
上記テキストについてレビューしてください。
問題点を箇条書きで、重要度（高/中/低）とともに記述してください。
"""


def load_rules(rules_dir: Path, section_label: str) -> dict[str, Any] | None:
    """セクションラベルに対応するルールファイルを読み込む。

    Args:
        rules_dir: ルールYAMLが格納されたディレクトリ。
        section_label: チャンクのラベル（セクションタイトル等）。

    Returns:
        ルール辞書。対応するファイルがなければ None。
    """
    # ラベルの先頭部分でファイル名を推測（小文字化・空白→アンダースコア）
    candidates = _label_to_candidates(section_label)
    for name in candidates:
        path = rules_dir / f"{name}.yaml"
        if path.exists():
            with path.open(encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                return loaded
    return None


def build_messages(chunk: Chunk, rules: dict[str, Any] | None) -> list[dict[str, str]]:
    """OpenAI messages 形式のリストを構築する。

    Args:
        chunk: レビュー対象のチャンク。
        rules: ルール辞書（None の場合は汎用プロンプトを使用）。

    Returns:
        [{"role": "system", ...}, {"role": "user", ...}] 形式のリスト。
    """
    system_content = SYSTEM_PROMPT
    if rules is not None:
        system_content += _format_rules(rules)

    user_content = (
        f"## セクション: {chunk.label}\n\n```latex\n{chunk.content}\n```{_OUTPUT_INSTRUCTION}"
    )

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


# ------------------------------------------------------------------
# 内部ヘルパー
# ------------------------------------------------------------------


def _label_to_candidates(label: str) -> list[str]:
    """ラベル文字列からルールファイル名の候補リストを生成する。"""
    # " > " で分割した先頭部分を正規化
    parts = [p.strip() for p in label.split(">")]
    candidates: list[str] = []
    for part in parts:
        normalized = part.lower().replace(" ", "_").replace("　", "_")
        # 英語キーワードへのマッピング
        for keyword in _KNOWN_SECTIONS:
            if keyword in normalized:
                candidates.append(keyword)
        candidates.append(normalized)
    return candidates


_KNOWN_SECTIONS = [
    "abstract",
    "introduction",
    "method",
    "result",
    "discussion",
    "conclusion",
    "title",
]


def _format_rules(rules: dict[str, Any]) -> str:
    """ルール辞書をシステムプロンプト追記用テキストに変換する。"""
    lines: list[str] = ["\n\n## セクション固有のルール\n"]

    section = rules.get("section", "")
    if section:
        lines.append(f"対象セクション: {section}\n")

    meta = rules.get("meta", {})
    if isinstance(meta, dict):
        desc = meta.get("description", "")
        if desc:
            lines.append(f"\n構造の説明:\n{desc}\n")

    elements = rules.get("elements", [])
    if isinstance(elements, list):
        lines.append("\n必須要素:\n")
        for elem in elements:
            if not isinstance(elem, dict):
                continue
            name = elem.get("name", "")
            description = elem.get("description", "")
            lines.append(f"- **{name}**: {description}\n")

    return "".join(lines)
