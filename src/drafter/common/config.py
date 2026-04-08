"""drafter の設定管理。

drafter.yaml（リポジトリルートまたは指定パス）を読み込み、
環境変数でオーバーライドする（オプションC）。

環境変数:
    DRAFTER_LLM_ENDPOINT          LLM APIのエンドポイントURL
    DRAFTER_LLM_MODEL             使用するモデル名
    DRAFTER_LLM_MAX_CONTEXT_TOKENS コンテキスト長の上限（整数）
    DRAFTER_API_KEY               APIキー（必須）
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class LLMConfig:
    """LLM APIの接続設定。"""

    endpoint: str = "https://api.openai.com/v1"
    model: str = "gpt-4o"
    max_context_tokens: int = 128_000
    api_key: str = ""


@dataclass
class DrafterConfig:
    """drafter 全体の設定。"""

    llm: LLMConfig = field(default_factory=LLMConfig)


def load_config(config_path: Path | None = None) -> DrafterConfig:
    """設定を読み込む。

    Args:
        config_path: drafter.yaml のパス。省略時はカレントディレクトリと
                     ワークスペースルートを順に探索する。

    Returns:
        DrafterConfig インスタンス。
    """
    raw: dict[str, object] = {}

    # 1. 設定ファイルを探して読み込む
    resolved_path = _find_config(config_path)
    if resolved_path is not None:
        with resolved_path.open(encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
        if isinstance(loaded, dict):
            raw = loaded

    # 2. LLMConfig を構築（設定ファイル値をベースに）
    llm_raw: dict[str, object] = {}
    if isinstance(raw.get("llm"), dict):
        llm_raw = raw["llm"]  # type: ignore[assignment]

    llm = LLMConfig(
        endpoint=str(llm_raw.get("endpoint", LLMConfig.endpoint)),
        model=str(llm_raw.get("model", LLMConfig.model)),
        max_context_tokens=int(
            str(llm_raw.get("max_context_tokens", LLMConfig.max_context_tokens))
        ),
        api_key=str(llm_raw.get("api_key", LLMConfig.api_key)),
    )

    # 3. 環境変数でオーバーライド
    if endpoint := os.getenv("DRAFTER_LLM_ENDPOINT"):
        llm.endpoint = endpoint
    if model := os.getenv("DRAFTER_LLM_MODEL"):
        llm.model = model
    if max_tokens_str := os.getenv("DRAFTER_LLM_MAX_CONTEXT_TOKENS"):
        llm.max_context_tokens = int(max_tokens_str)
    if api_key := os.getenv("DRAFTER_API_KEY"):
        llm.api_key = api_key

    return DrafterConfig(llm=llm)


def _find_config(explicit: Path | None) -> Path | None:
    """設定ファイルのパスを解決する。

    探索順:
        1. config/drafter.yaml（プロジェクトルートの config/ ディレクトリ）
        2. drafter.yaml（プロジェクトルート直下）
    カレントディレクトリから上位へ最大5階層まで探索する。
    """
    if explicit is not None:
        return explicit if explicit.exists() else None

    current = Path.cwd()
    for _ in range(5):
        for candidate in (current / "config" / "drafter.yaml", current / "drafter.yaml"):
            if candidate.exists():
                return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent

    return None
