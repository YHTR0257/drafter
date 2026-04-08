"""LaTeXファイルの自動修正フォーマッタ。

lintパス後に任意適用できる、自動修正可能な整形処理を提供する。
"""

from __future__ import annotations

import re
from pathlib import Path

# 3行以上連続する空行を2行に圧縮するパターン
_MULTI_BLANK_RE = re.compile(r"\n{3,}")


def format_file(path: Path) -> bool:
    """ファイルを整形し、変更があった場合は True を返す。

    修正内容:
    - 行末スペースの除去
    - 連続空行の正規化（3行以上 → 2行）

    Args:
        path: 整形対象の .tex ファイル。

    Returns:
        ファイルが変更された場合 True、変更なしの場合 False。
    """
    original = path.read_text(encoding="utf-8")
    result = _apply_formatting(original)
    if result == original:
        return False
    path.write_text(result, encoding="utf-8")
    return True


def _apply_formatting(content: str) -> str:
    """整形処理を適用してテキストを返す。"""
    # 行末スペースを除去
    lines = [line.rstrip() for line in content.splitlines()]
    joined = "\n".join(lines)

    # 末尾改行を保持
    if content.endswith("\n"):
        joined += "\n"

    # 連続空行を最大2行に圧縮
    joined = _MULTI_BLANK_RE.sub("\n\n", joined)

    return joined
