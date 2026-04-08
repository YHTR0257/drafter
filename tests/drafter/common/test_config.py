"""tests/drafter/common/test_config.py

common/config.py のミラーテスト。
"""

from pathlib import Path

import pytest

from drafter.common.config import DrafterConfig, LLMConfig, load_config


# ---------------------------------------------------------------------------
# デフォルト値
# ---------------------------------------------------------------------------


class TestDefaults:
    def test_llm_config_defaults(self) -> None:
        cfg = LLMConfig()
        assert cfg.endpoint == "https://api.openai.com/v1"
        assert cfg.model == "gpt-4o"
        assert cfg.max_context_tokens == 128_000
        assert cfg.api_key == ""

    def test_drafter_config_has_llm(self) -> None:
        cfg = DrafterConfig()
        assert isinstance(cfg.llm, LLMConfig)


# ---------------------------------------------------------------------------
# load_config - 設定ファイルなし
# ---------------------------------------------------------------------------


class TestLoadConfigNoFile:
    def test_returns_drafter_config(self, tmp_path: Path) -> None:
        cfg = load_config(config_path=tmp_path / "nonexistent.yaml")
        assert isinstance(cfg, DrafterConfig)

    def test_uses_defaults_when_no_file(self, tmp_path: Path) -> None:
        cfg = load_config(config_path=tmp_path / "nonexistent.yaml")
        assert cfg.llm.model == "gpt-4o"


# ---------------------------------------------------------------------------
# load_config - 設定ファイルあり
# ---------------------------------------------------------------------------


class TestLoadConfigFromFile:
    def test_reads_endpoint(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "drafter.yaml"
        cfg_file.write_text("llm:\n  endpoint: http://localhost:8080/v1\n", encoding="utf-8")
        cfg = load_config(config_path=cfg_file)
        assert cfg.llm.endpoint == "http://localhost:8080/v1"

    def test_reads_model(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "drafter.yaml"
        cfg_file.write_text("llm:\n  model: llama3\n", encoding="utf-8")
        cfg = load_config(config_path=cfg_file)
        assert cfg.llm.model == "llama3"

    def test_reads_max_context_tokens(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "drafter.yaml"
        cfg_file.write_text("llm:\n  max_context_tokens: 4096\n", encoding="utf-8")
        cfg = load_config(config_path=cfg_file)
        assert cfg.llm.max_context_tokens == 4096

    def test_partial_file_uses_defaults_for_missing_keys(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "drafter.yaml"
        cfg_file.write_text("llm:\n  model: custom\n", encoding="utf-8")
        cfg = load_config(config_path=cfg_file)
        assert cfg.llm.model == "custom"
        assert cfg.llm.endpoint == "https://api.openai.com/v1"

    def test_empty_file_uses_defaults(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "drafter.yaml"
        cfg_file.write_text("", encoding="utf-8")
        cfg = load_config(config_path=cfg_file)
        assert cfg.llm.model == "gpt-4o"


# ---------------------------------------------------------------------------
# load_config - 環境変数オーバーライド
# ---------------------------------------------------------------------------


class TestLoadConfigEnvOverride:
    def test_endpoint_overridden_by_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DRAFTER_LLM_ENDPOINT", "http://env-host/v1")
        cfg = load_config(config_path=tmp_path / "nonexistent.yaml")
        assert cfg.llm.endpoint == "http://env-host/v1"

    def test_model_overridden_by_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DRAFTER_LLM_MODEL", "env-model")
        cfg = load_config(config_path=tmp_path / "nonexistent.yaml")
        assert cfg.llm.model == "env-model"

    def test_max_tokens_overridden_by_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DRAFTER_LLM_MAX_CONTEXT_TOKENS", "8192")
        cfg = load_config(config_path=tmp_path / "nonexistent.yaml")
        assert cfg.llm.max_context_tokens == 8192

    def test_api_key_overridden_by_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DRAFTER_API_KEY", "sk-test")
        cfg = load_config(config_path=tmp_path / "nonexistent.yaml")
        assert cfg.llm.api_key == "sk-test"

    def test_env_overrides_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        cfg_file = tmp_path / "drafter.yaml"
        cfg_file.write_text("llm:\n  model: file-model\n", encoding="utf-8")
        monkeypatch.setenv("DRAFTER_LLM_MODEL", "env-model")
        cfg = load_config(config_path=cfg_file)
        assert cfg.llm.model == "env-model"
