# SPEC.md

`drafter` リポジトリの詳細仕様（構成・テスト方針・制約）。日常的なコマンドは [AGENTS.md](AGENTS.md) を参照。

## Architecture

### Python package (`src/drafter/`)

| パッケージ | 責務 |
|---|---|
| `common/tex_parser.py` | `\input{}` 展開・セクション階層抽出・環境認識・トークン推定。linter/reviewer 共通基盤 |
| `common/config.py` | `config/drafter.yaml` + 環境変数でLLM設定を管理（オプションC方式） |
| `converter/pipeline.py` | LaTeX → DOCX。`\input{}` 展開 → 中間 .tex → Pandoc の2段変換 |
| `converter/config.py` | Pandoc コマンドの組み立てと中間ファイルのパス導出 |
| `converter/word_template.py` | Pandoc `--reference-doc` 用 Word テンプレートの組み立て |
| `linter/pipeline.py` | LaTeX 構文・Pandoc互換チェック。`linter/rules/pandoc_compat.py` にルール実装 |
| `formatter/pipeline.py` | 行末スペース除去・連続空行正規化・和文約物の正規化（自動修正） |
| `reviewer/splitter.py` | Document をコンテキスト長以内のチャンクに段階分割 |
| `reviewer/prompt_builder.py` | チャンク + `templates/rules/*.yaml` + 出力指示からプロンプト構築 |
| `reviewer/client.py` | OpenAI互換APIクライアント（llama.cpp も対応、APIキー不要で動作） |
| `reviewer/pipeline.py` | review 全体の実行制御 → `dist/review-report.md` 出力 |

各 pipeline は `python -m drafter.<module>.pipeline` で直接起動できる（click CLI）。

### Paper structure (`papers/<name>/`)

Each paper directory contains:
- `main.tex` — top-level document (inputs section files)
- `sections/` — per-section `.tex` files (introduction, method, result, discussion, conclusion)
- `.latexmkrc` — LuaLaTeX build config
- `Makefile` — includes `../../templates/make/common.mk`
- `dist/` — build output (gitignored)

Shared bibliography lives in `papers/bib/*.bib`.

### Templates (`templates/`)

- `make/common.mk` — shared Makefile rules for all papers; defines
  `pdf`, `docx`, `docx-review`, `review`, `lint`, `clean` targets
- `rules/*.yaml` — section-structure rules (used by the reviewer); one file per section
  (abstract, introduction, method, result, discussion, title)
- `pandoc/defaults.yaml` — Pandoc 変換のデフォルト設定（`from: latex+raw_tex`, `to: docx`）
- `msword/` — Pandoc `--reference-doc` に渡す Word テンプレート（**gitignore 対象**）
- `msword/ref/` — 体裁の参照元となる実物の Word 文書。テンプレートを直接編集するのではなく、
  `src/drafter/converter/word_template.py` を正としてここに合わせる

#### DOCX 変換（2段構成）

`from: latex+raw_tex` では Pandoc が `\input{}` を展開せず raw block として保持し、
docx ライターがそれを捨ててしまう（本文が丸ごと消える）。そのため変換は2段構成になっている。

1. `TexParser.resolve_inputs()` で `\input{}` を再帰展開し、`dist/<出力名>.expanded.tex` へ書き出す
2. その中間ファイルを Pandoc に渡す

中間ファイルは `dist/` にあるので `make clean` で消える。出力ファイル名から導くため、
`docx` と `docx-review` を並列生成しても衝突しない。

中間ファイルが `dist/` にある結果、Pandoc の既定の画像探索先も `dist/` になる。
Pandoc は `\graphicspath` を解釈しないので、`--resource-path`（`common.mk` の
`PANDOC_RESOURCE_FLAGS`）で `.` と `$(FIGURES_DIR)` を明示している。

#### Word テンプレート

`make word-templates` で `templates/msword/` に3種類を生成する。体裁は
`msword/ref/Graduation_paper_split.docx` で実際に使われているスタイルに合わせている
（本文 Times New Roman + ＭＳ 明朝 12pt、見出し Arial + ＭＳ ゴシック、`第N章` 自動採番）。

| ファイル | 用途 | 本文 | 1行 | 行送り |
|---|---|---|---|---|
| `template-article.docx` | 長文。1段組・章節項の4階層を採番・章ごとに改ページ。`WORD_TEMPLATE` の既定値 | 12pt | 40.1字 | 1.67行 |
| `template-review.docx` | 校閲用。1段組・行番号あり・章見出しのみ採番 | 12pt | 40.1字 | 2.00行 |
| `template-short.docx` | ショートペーパー。2段組・章節の2階層を採番・改ページなし | 10.5pt | 21.9字 | 1.67行 |

参考 docx から意図的に変えている組版パラメータ:

- **余白 1440 → 1134（20mm）**。1440 のままだと 12pt 本文で 1 行 37 字しか入らず短い
- **段間 720 → 425（7.5mm）**。720 は 2 段組には広すぎる
- **行グリッド 466 → 400**（`TIGHT_LINE_PITCH`）。466 は 12pt で約 1.94 行と広すぎる
- **2段組のみ本文 10.5pt**（`COMPACT_BODY_SIZE`）。12pt では 1 段が 17 字しか入らない
  行グリッドも 350（`COMPACT_LINE_PITCH`）に合わせ、article と同じ約 1.67 行の比率にしている

生成物は gitignore 対象なので、クローン直後は `make word-templates` が必要。
テンプレートの体裁を変えるときは docx を直接編集せず `word_template.py` を修正して再生成する。

### 設定ファイル (`config/`)

- `config/drafter.yaml.example` — LLM設定のサンプル。各利用者がコピーして `config/drafter.yaml` を作成する
- `config/drafter.yaml` — 実際の設定（**gitignore 対象**）。`DRAFTER_API_KEY` 環境変数でAPIキーを注入
- llama.cpp の場合は `api_key` 不要（エンドポイントを `http://localhost:8080/v1` に設定するだけ）

### AIエージェント設定

`AGENTS.md` と `.agents/` を正本とし、ツール固有のパスは相対 symlink で共有する。
編集は常に正本側で行う。

| 正本 | Claude Code | Codex |
|---|---|---|
| `AGENTS.md` | `CLAUDE.md` -> `AGENTS.md` | 正本を直接参照 |
| `.agents/skills/` | `.claude/skills` -> `../.agents/skills` | 正本を直接参照 |
| `.agents/agents/` | `.claude/agents` -> `../.agents/agents` | 共有不可（下記） |

- カスタムエージェント定義は共有できない。Claude Code は Markdown + YAML frontmatter
  （`.claude/agents/*.md`）、Codex は TOML（`.codex/agents/*.toml`）で形式が異なる。
  `.agents/agents/` は Claude Code 形式の正本で、`.codex/agents` は置かない
- スキルは `<skill-name>/SKILL.md` 形式で共有する。frontmatter の `name` と `description` は必須
- `.claude/settings.json` は Claude 固有のため実ファイルのまま管理する

### Fonts

Windows/Office-compatible fonts are bundled in `.devcontainer/fonts/` and referenced by path
in `main.tex` via `fontspec`/`luatexja-fontspec`.

## Testing

テストは `src/drafter/` の構造をミラーした `tests/drafter/` に配置する。

```
src/drafter/                    tests/drafter/
├── common/tex_parser.py    →   ├── common/test_tex_parser.py
├── common/config.py        →   ├── common/test_config.py
├── reviewer/splitter.py    →   ├── reviewer/test_splitter.py
├── reviewer/prompt_builder →   ├── reviewer/test_prompt_builder.py
├── formatter/pipeline.py   →   ├── formatter/test_pipeline.py
├── linter/rules/pandoc_compat→ ├── linter/rules/test_pandoc_compat.py
├── converter/config.py     →   ├── converter/test_config.py（中間ファイルのパス導出含む）
└── converter/word_template →   └── converter/test_word_template.py
```

- pytest の設定は `pyproject.toml` の `[tool.pytest.ini_options]` で管理（`pytest.ini` は不要）
- `pipeline.py` は外部依存（API・Pandoc・latexmk）があるためユニットテスト対象外。構成要素を個別にテストする方針
- テストヘルパーは各テストファイル内にローカル定義し、共通 `conftest.py` は設けない（依存関係を明示的に保つ）

## Key constraints

- Papers use **LuaLaTeX** (not pdflatex). The `jlreq` document class is used for Japanese
  typesetting.
- `.tex`, `.pdf`, `.png` files must **not** be committed (enforced by prek hook).
- Python package requires `>=3.12`; type checking is strict mypy.
- `ruff` line length is 100, target version py311.
- 新しいモジュールを追加したらミラーテストを同時に作成すること。
