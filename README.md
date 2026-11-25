# drafter

LaTeX論文執筆環境とPythonユーティリティ群。Dev Container上で動作し、PDF・Word出力およびAIによるセクション校閲をサポートする。

## 特徴

- **LuaLaTeX** による日本語・英語論文のPDFコンパイル（`jlreq`クラス使用）
- **Pandoc** 経由でWordファイル（`.docx`）への変換
- **AIレビュー**：セクション構造ルール（YAML定義）に基づくLLM校閲
- **pre-commitフック（prek）**：ruff/mypy/editorconfig/YAML検証の自動実行

## 前提

- Docker + VS Code Dev Container（または GitHub Codespaces）
- Claude ProまたはMaxプラン（AI機能を使用する場合）

## セットアップ

Dev Containerを開くと `post-create.sh` が自動実行され、`prek install` まで完了する。

## Compose 検証（Issue #2）

ホスト編集 + コンテナビルドの検証用。旧環境の撤去は未実施。
Docker Compose v2 を使用する。ホストに TeX / Pandoc / Python はビルド用途では不要。

```bash
cp .env.example .env
# .env の論文・bib・フォントのパスを設定（make が UID/GID を自動取得）
# main.tex のフォント指定: Path=/usr/share/fonts/ms-fonts/
make build
make up                         # 常駐コンテナ（任意）
make bash                       # 一時コンテナでシェルを開く
make build-pdf PAPER=<name>
make build-docx PAPER=<name>
make build-docx PAPER=<name> FORMAT=short  # article / short / review
make down
```

`PAPERS_DIR` は論文ディレクトリ群の親、`BIB_DIR` は共有 bib の実体。
ホスト側の絶対パス symlink はコンテナで解決できないので、実体を指定する。
フォントは読み取り専用マウントし、イメージに同梱しない。
依存関係を変更した場合は `make build` を再実行する。
DOCX は `FORMAT=article`（既定・長文）、`short`（2段組）、`review`（校閲用）で体裁を選ぶ。
いずれも `dist/main.docx` に出力し、再実行時は上書きする。
テンプレートは未生成時に自動生成する。
既定では lint エラーで停止する。既知の指摘を保留して出力を確認する場合のみ
`make build-docx PAPER=<name> FORMAT=article SKIP_LINT=1` で明示的にスキップできる。
`make word-templates` で明示的に生成することもできる。
コンテナ内は `uv run` で Python / latexmk / Pandoc を実行し、make は使わない。
WSL では Linux のパスとユーザー ID を設定する（実機検証は未実施）。

既存論文を変更せずサンプルで確認する場合（ホストに Bash / Python 3 が必要）:

```bash
docker compose --env-file .env.example build
FONTS_DIR=/absolute/path/to/fonts bash scripts/verify-compose.sh
```

検証は `times.ttf` / `msmincho.ttc` を使う。
フォントパス未指定時は既存のローカルフォント置き場を利用する。
出力先はスクリプトが表示する一時ディレクトリ。

## ディレクトリ構成

```
drafter/
├── papers/
│   ├── bib/              # 共有BibTeXファイル群
│   ├── 01-thesis/        # 論文ごとのディレクトリ
│   │   ├── main.tex
│   │   ├── sections/     # introduction, method, result, discussion, conclusion
│   │   ├── .latexmkrc
│   │   └── Makefile      # common.mk をinclude
│   └── 02-wccm-paper/
├── templates/
│   ├── make/common.mk    # 全論文共通のMakeルール
│   ├── rules/            # AIレビュー用セクション構造ルール（YAML）
│   └── msword/           # Pandoc用Wordテンプレート
├── src/drafter/          # Pythonユーティリティ
│   ├── converter/        # LaTeX → DOCX変換
│   ├── linter/           # LaTeX構文チェック
│   ├── formatter/        # LaTeXフォーマット
│   └── reviewer/         # LLM校閲ランナー
├── figures/              # 論文共通の図ファイル
└── pyproject.toml
```

## 使い方

### 論文のビルド

論文ディレクトリ（`papers/<name>/`）で実行する。

```bash
make pdf      # lint → LuaLaTeX → dist/main.pdf
make docx     # lint → Pandoc  → dist/main.docx
make review   # AIレビュー     → dist/review-report.md
make lint     # 構文チェックのみ
make clean    # dist/ を削除
```

ホストのリポジトリルートからは `make build-pdf PAPER=<name>` 等を使う。
上記の論文別 Makefile は既存環境向けに残している。

### Pythonツールの実行

```bash
uv run python -m drafter.<module>
uv run ruff check --fix src/
uv run mypy
```

## 論文の追加

1. `papers/<name>/` ディレクトリを作成する
2. `sections/` に `introduction.tex` 等を配置する
3. `main.tex` で各セクションを `\input` する
4. 以下の内容で `Makefile` を作成する：

```makefile
MAIN_TEX      = main.tex
WORD_TEMPLATE = template-a.docx
include ../../templates/make/common.mk
```

5. `.latexmkrc` でLuaLaTeX設定とbibパスを指定する

## セクション構造ルール

`templates/rules/` 以下にセクションごとのYAMLが定義されている。AIレビュー時にこのルールと照合して構造の過不足を指摘する。

| ファイル | セクション | 必須 |
|---|---|---|
| `abstract.yaml` | Abstract | 任意 |
| `introduction.yaml` | Introduction | 必須 |
| `method.yaml` | Method | 必須 |
| `result.yaml` | Result | 必須 |
| `discussion.yaml` | Discussion | 必須 |
| `title.yaml` | Title | 任意 |

## 注意事項

- `.tex`、`.pdf`、`.png` ファイルはコミット禁止（prek hookで強制）
- フォントは `.devcontainer/fonts/` にバンドルされており、`main.tex` から絶対パスで参照する
- BibTeXファイルは `papers/bib/` に集約し、論文間で共有する
