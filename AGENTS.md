# AGENTS.md

This file provides guidance to AI coding agents (Claude Code, OpenAI Codex) when working with code
in this repository. `CLAUDE.md` is a symlink to this file; edit `AGENTS.md`.

## Overview

`drafter` is a LaTeX academic paper writing environment with Python utilities. It supports compiling papers to PDF (via LuaLaTeX/latexmk) and Word DOCX (via Pandoc), with AI-assisted review using section-structure rules.

## Commands

### Container builds (run on the host)

```bash
task --list                         # list available tasks
task help                           # commands, examples and variables
task setup os=macos                 # or os=wsl; interactive setup
task create:paper paper=<paper-name>
task docker:build                   # build the Docker image
task docker:up                      # start an idle container (optional)
task docker:bash                    # open a disposable shell
task compile:pdf paper=<paper-name>
task compile:docx paper=<paper-name>
task compile:docx paper=<paper-name> format=short  # article / short / review
task docker:down
```

`Taskfile.yml` includes definitions from `tools/go-task/`; see its README for wiring.
Tasks call `uv run drafter <subcommand>`. The CLI reads `.env` and detects host UID/GID.
Paper processing runs in Compose; creation, setup and figure generation run on the host.
Optional `<PAPERS_DIR>/<paper>/paper.yml` provides defaults; CLI values take precedence.
Setup and repository layout live under `docs/`; README links to them.

### Python (run on the host for development)

```bash
uv run python -m drafter.<module>   # run a drafter module
uv run pytest                        # run all tests
uv run pytest tests/drafter/common/ # run tests for a specific module
uv run mypy src/                     # type check (strict)
uv run ruff check --fix src/         # lint
uv run ruff format src/              # format
```

### Paper checks (run on the host)

```bash
task review paper=<paper-name> # AI review → dist/review-report.md
task lint paper=<paper-name>   # check and format TeX (modifies input)
```

### Word templates (run on the host)

```bash
task compile:templates  # generate Word templates through the container
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
