# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
make pdf      # lint → LaTeX → dist/main.pdf
make docx     # lint → Pandoc → dist/main.docx
make review   # AI review via drafter.reviewer.runner → dist/review-report.md
make lint     # run drafter.linter.runner only
make clean    # remove dist/
```

### Bulk operations (run from `/workspace`)

```bash
make pdf-all    # build all papers to PDF
make docx-all   # build all papers to DOCX
make review-all # review all papers
make lint-all   # lint all papers
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

## Architecture

### Python package (`src/drafter/`)

| パッケージ | 責務 |
|---|---|
| `common/tex_parser.py` | `\input{}` 展開・セクション階層抽出・環境認識・トークン推定。linter/reviewer 共通基盤 |
| `common/config.py` | `config/drafter.yaml` + 環境変数でLLM設定を管理（オプションC方式） |
| `converter/runner.py` | LaTeX → DOCX（Pandoc呼び出し）。`converter/config.py` でコマンド組み立て |
| `linter/runner.py` | LaTeX 構文・Pandoc互換チェック。`linter/rules/pandoc_compat.py` にルール実装 |
| `linter/formatter.py` | 行末スペース除去・連続空行正規化（自動修正） |
| `reviewer/splitter.py` | Document をコンテキスト長以内のチャンクに段階分割 |
| `reviewer/prompt_builder.py` | チャンク + `templates/rules/*.yaml` + 出力指示からプロンプト構築 |
| `reviewer/client.py` | OpenAI互換APIクライアント（llama.cpp も対応、APIキー不要で動作） |
| `reviewer/runner.py` | review 全体の実行制御 → `dist/review-report.md` 出力 |

各 runner は `python -m drafter.<module>.runner` で直接起動できる（click CLI）。

### Paper structure (`papers/<name>/`)

Each paper directory contains:
- `main.tex` — top-level document (inputs section files)
- `sections/` — per-section `.tex` files (introduction, method, result, discussion, conclusion)
- `.latexmkrc` — LuaLaTeX build config
- `Makefile` — includes `../../templates/make/common.mk`
- `dist/` — build output (gitignored)

Shared bibliography lives in `papers/bib/*.bib`.

### Templates (`templates/`)

- `make/common.mk` — shared Makefile rules for all papers; defines `pdf`, `docx`, `review`, `lint`, `clean` targets
- `rules/*.yaml` — section-structure rules (used by the reviewer); one file per section (abstract, introduction, method, result, discussion, title)
- `pandoc/defaults.yaml` — Pandoc 変換のデフォルト設定（`from: latex+raw_tex`, `to: docx`）
- `msword/` — Word template files for Pandoc output (gitignored from commits)

### 設定ファイル (`config/`)

- `config/drafter.yaml.example` — LLM設定のサンプル。各利用者がコピーして `config/drafter.yaml` を作成する
- `config/drafter.yaml` — 実際の設定（**gitignore 対象**）。`DRAFTER_API_KEY` 環境変数でAPIキーを注入
- llama.cpp の場合は `api_key` 不要（エンドポイントを `http://localhost:8080/v1` に設定するだけ）

### Fonts

Windows/Office-compatible fonts are bundled in `.devcontainer/fonts/` and referenced by path in `main.tex` via `fontspec`/`luatexja-fontspec`.

## Testing

テストは `src/drafter/` の構造をミラーした `tests/drafter/` に配置する。

```
src/drafter/                    tests/drafter/
├── common/tex_parser.py    →   ├── common/test_tex_parser.py
├── common/config.py        →   ├── common/test_config.py
├── reviewer/splitter.py    →   ├── reviewer/test_splitter.py
├── reviewer/prompt_builder →   ├── reviewer/test_prompt_builder.py
├── linter/formatter.py     →   ├── linter/test_formatter.py
├── linter/rules/pandoc_compat→ ├── linter/rules/test_pandoc_compat.py
└── converter/config.py     →   └── converter/test_config.py
```

- pytest の設定は `pyproject.toml` の `[tool.pytest.ini_options]` で管理（`pytest.ini` は不要）
- `runner.py` は外部依存（API・Pandoc・latexmk）があるためユニットテスト対象外。構成要素を個別にテストする方針
- テストヘルパーは各テストファイル内にローカル定義し、共通 `conftest.py` は設けない（依存関係を明示的に保つ）

## Key constraints

- Papers use **LuaLaTeX** (not pdflatex). The `jlreq` document class is used for Japanese typesetting.
- `.tex`, `.pdf`, `.png` files must **not** be committed (enforced by prek hook).
- Python package requires `>=3.12`; type checking is strict mypy.
- `ruff` line length is 100, target version py311.
- 新しいモジュールを追加したらミラーテストを同時に作成すること。
