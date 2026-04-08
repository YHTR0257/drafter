# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`drafter` is a LaTeX academic paper writing environment with Python utilities. It supports compiling papers to PDF (via LuaLaTeX/latexmk) and Word DOCX (via Pandoc), with AI-assisted review using section-structure rules.

## Commands

### Python (run from `/workspace`)

```bash
uv run python -m drafter.<module>   # run a drafter module
uv run mypy                          # type check (strict)
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

Hooks enforce: YAML/TOML validity, trailing whitespace, ruff lint+format, mypy, editorconfig line length. `.png`, `.pdf`, and `.tex` files are **prohibited from being committed**.

## Architecture

### Python package (`src/drafter/`)

Three subpackages, each with an `equation.py` module and a `runner.py` entry point (invoked by Make):

- `converter/` — LaTeX → DOCX via Pandoc (`drafter.converter.runner`)
- `linter/` — LaTeX syntax/compatibility checks (`drafter.linter.runner`)
- `formatter/` — LaTeX formatting utilities (`drafter.formatter`)
- `reviewer/` — LLM-based section review against YAML rules (`drafter.reviewer.runner`)

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
- `msword/` — Word template files for Pandoc output (gitignored from commits)

### Fonts

Windows/Office-compatible fonts are bundled in `.devcontainer/fonts/` and referenced by path in `main.tex` via `fontspec`/`luatexja-fontspec`.

## Key constraints

- Papers use **LuaLaTeX** (not pdflatex). The `jlreq` document class is used for Japanese typesetting.
- `.tex`, `.pdf`, `.png` files must **not** be committed (enforced by prek hook).
- Python package requires `>=3.12`; type checking is strict mypy.
- `ruff` line length is 100, target version py311.
