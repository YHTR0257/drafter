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

全論文を一括処理する場合はリポジトリルートから：

```bash
make pdf-all
make docx-all
make review-all
make lint-all
```

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
