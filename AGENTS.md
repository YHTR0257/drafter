# AGENTS.md

This file provides guidance to AI coding agents (Claude Code, OpenAI Codex) when working with code
in this repository. `CLAUDE.md` is a symlink to this file; edit `AGENTS.md`.

## Overview

`drafter` is a LaTeX academic paper writing environment with Python utilities. It supports compiling papers to PDF (via LuaLaTeX/latexmk) and Word DOCX (via Pandoc), with AI-assisted review using section-structure rules.

## Commands

### Python (run from `/workspace`)

```bash
uv run python -m drafter.<module>   # run a drafter module
uv run pytest                        # run all tests
uv run pytest tests/drafter/common/ # run tests for a specific module
uv run mypy src/                     # type check (strict)
uv run ruff check --fix src/         # lint
uv run ruff format src/              # format
```

### Paper build (run from `papers/<paper-name>/`)

```bash
make pdf         # lint → LaTeX → dist/main.pdf
make docx        # lint → Pandoc → dist/main.docx
make docx-review # 校閲用DOCX（1段組・行間2行・行番号） → dist/main-review.docx
make review      # AI review via drafter.reviewer.pipeline → dist/review-report.md
make lint        # run drafter.linter.pipeline only
make clean       # remove dist/
```

### Bulk operations (run from `/workspace`)

```bash
make word-templates  # Wordテンプレートを生成（templates/msword/）
make pdf-all         # build all papers to PDF
make docx-all        # build all papers to DOCX
make docx-review-all # build all papers to review DOCX
make review-all      # review all papers
make lint-all        # lint all papers
```

### Pre-commit hooks (`prek`)

```bash
prek run    # run all hooks manually
```

Hooks enforce (defined in `prek.toml`):

| Hook | 内容 |
|---|---|
| `check-yaml`, `check-toml` | YAML/TOML の構文チェック |
| `end-of-file-fixer`, `trailing-whitespace` | 末尾空白・改行の正規化 |
| `ruff-check --fix`, `ruff-format` | Python lint + 自動修正 + フォーマット |
| `mypy` | 型チェック（strict）。`additional_dependencies` に `pyyaml types-PyYAML openai click` を指定済み |
| `editorconfig-checker` | 行長チェック（100文字） |
| `forbid-png-pdf-tex` | `.png`, `.pdf`, `.tex` ファイルのコミット禁止 |

## 詳細仕様

構成（`src/drafter/` の各パッケージ、`papers/`・`templates/`・`config/`・フォント）、テスト方針、
制約は [SPEC.md](SPEC.md) を参照。実装や構成を変更したら SPEC.md も更新すること。
