"""tests/drafter/reviewer/test_prompt_builder.py

reviewer/prompt_builder.py のミラーテスト。
"""

from pathlib import Path


from drafter.reviewer.prompt_builder import (
    SYSTEM_PROMPT,
    _label_to_candidates,
    build_messages,
    load_rules,
)
from drafter.reviewer.splitter import Chunk


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def make_chunk(label: str = "introduction", content: str = "\\section{intro}\ntext") -> Chunk:
    return Chunk(label=label, content=content, token_estimate=10)


def write_rule(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / f"{name}.yaml"
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# load_rules
# ---------------------------------------------------------------------------


class TestLoadRules:
    def test_returns_none_when_no_match(self, tmp_path: Path) -> None:
        result = load_rules(tmp_path, "unknown_section_xyz")
        assert result is None

    def test_loads_matching_yaml(self, tmp_path: Path) -> None:
        write_rule(tmp_path, "introduction", "section: introduction\nelements: []")
        result = load_rules(tmp_path, "introduction")
        assert result is not None
        assert result["section"] == "introduction"

    def test_label_with_greater_separator(self, tmp_path: Path) -> None:
        write_rule(tmp_path, "method", "section: method\nelements: []")
        result = load_rules(tmp_path, "method > 実験手法")
        assert result is not None

    def test_japanese_section_matches_english_keyword(self, tmp_path: Path) -> None:
        write_rule(tmp_path, "result", "section: result\nelements: []")
        # "result" が含まれるラベル
        result = load_rules(tmp_path, "result")
        assert result is not None

    def test_invalid_yaml_returns_none(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.yaml"
        p.write_text("- not: a: dict", encoding="utf-8")
        result = load_rules(tmp_path, "bad")
        assert result is None


# ---------------------------------------------------------------------------
# build_messages
# ---------------------------------------------------------------------------


class TestBuildMessages:
    def test_returns_two_messages(self) -> None:
        msgs = build_messages(make_chunk(), rules=None)
        assert len(msgs) == 2

    def test_first_message_is_system(self) -> None:
        msgs = build_messages(make_chunk(), rules=None)
        assert msgs[0]["role"] == "system"

    def test_second_message_is_user(self) -> None:
        msgs = build_messages(make_chunk(), rules=None)
        assert msgs[1]["role"] == "user"

    def test_system_contains_base_prompt(self) -> None:
        msgs = build_messages(make_chunk(), rules=None)
        assert SYSTEM_PROMPT.strip()[:20] in msgs[0]["content"]

    def test_user_contains_chunk_label(self) -> None:
        chunk = make_chunk(label="method")
        msgs = build_messages(chunk, rules=None)
        assert "method" in msgs[1]["content"]

    def test_user_contains_chunk_content(self) -> None:
        chunk = make_chunk(content="x = y + z")
        msgs = build_messages(chunk, rules=None)
        assert "x = y + z" in msgs[1]["content"]

    def test_rules_appended_to_system(self, tmp_path: Path) -> None:
        rules = {
            "section": "introduction",
            "meta": {"description": "funnel structure"},
            "elements": [{"name": "背景", "description": "研究背景を述べる"}],
        }
        msgs = build_messages(make_chunk(), rules=rules)
        assert "背景" in msgs[0]["content"]


# ---------------------------------------------------------------------------
# _label_to_candidates (内部関数)
# ---------------------------------------------------------------------------


class TestLabelToCandidates:
    def test_simple_label(self) -> None:
        result = _label_to_candidates("introduction")
        assert "introduction" in result

    def test_nested_label(self) -> None:
        result = _label_to_candidates("method > 実験手法")
        assert "method" in result

    def test_known_section_keywords_matched(self) -> None:
        result = _label_to_candidates("result")
        assert "result" in result
