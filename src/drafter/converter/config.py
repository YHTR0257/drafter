"""Pandoc変換の設定・コマンド構築。

defaults.yaml の読み込みと pandoc コマンドライン引数の組み立てを行う。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_pandoc_defaults(path: Path) -> dict[str, Any]:
    """Pandoc defaults YAML ファイルを読み込む。

    Args:
        path: defaults.yaml のパス。

    Returns:
        パースされた辞書。ファイルが存在しない場合は空辞書。
    """
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        loaded = yaml.safe_load(f)
    return loaded if isinstance(loaded, dict) else {}


def build_pandoc_command(
    input_path: Path,
    output: Path,
    bibliography: list[Path],
    template: Path | None,
    defaults: Path | None,
) -> list[str]:
    """pandoc コマンドライン引数のリストを組み立てる。

    Args:
        input_path: 変換元の LaTeX ファイル。
        output: 出力先（.docx 等）。
        bibliography: 参照する .bib ファイルのリスト。
        template: Word テンプレート（--reference-doc）。
        defaults: Pandoc defaults YAML ファイル。

    Returns:
        subprocess に渡せる文字列リスト。
    """
    cmd: list[str] = ["pandoc", str(input_path), "-o", str(output)]

    if defaults is not None and defaults.exists():
        cmd += ["--defaults", str(defaults)]

    for bib in bibliography:
        cmd += [f"--bibliography={bib}"]

    if template is not None:
        cmd += [f"--reference-doc={template}"]

    # 参考文献の自動処理
    if bibliography:
        cmd += ["--citeproc"]

    return cmd
