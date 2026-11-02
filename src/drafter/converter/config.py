"""Pandoc変換の設定・コマンド構築。

defaults.yaml の読み込みと pandoc コマンドライン引数の組み立てを行う。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def build_expanded_tex_path(output: Path) -> Path:
    """`\\input{}` 展開済み中間ファイルの出力先を返す。

    Pandoc に渡す前に `\\input{}` を解決した .tex を一度書き出す
    （`from: latex+raw_tex` では Pandoc 側が `\\input{}` を展開しないため）。

    出力ファイル名から導くので、docx と review-docx を並列生成しても
    中間ファイルの書き込みが衝突しない。

    Args:
        output: Pandoc の出力先（`dist/main.docx` 等）。

    Returns:
        中間ファイルのパス（`dist/main.expanded.tex` 等）。
    """
    return output.parent / f"{output.stem}.expanded.tex"


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
    resource_path: list[Path] | None = None,
) -> list[str]:
    """pandoc コマンドライン引数のリストを組み立てる。

    Args:
        input_path: 変換元の LaTeX ファイル。
        output: 出力先（.docx 等）。
        bibliography: 参照する .bib ファイルのリスト。
        template: Word テンプレート（--reference-doc）。
        defaults: Pandoc defaults YAML ファイル。
        resource_path: 画像などの探索先。Pandoc は \\graphicspath を解釈せず、
            既定の探索先も入力ファイルのあるディレクトリになるため明示が要る。

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

    if resource_path:
        cmd += [f"--resource-path={os.pathsep.join(str(p) for p in resource_path)}"]

    # 参考文献の自動処理
    if bibliography:
        cmd += ["--citeproc"]

    return cmd
