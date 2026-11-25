# Makeからの移行

定義元: [Taskの配線](../../tools/go-task/README.md)、[CLI](../../src/drafter/cli.py)。

## Phase 1: コマンド

### STEP 1: 新しいコマンドへ置き換える

| 旧コマンド | 新コマンド |
|---|---|
| `make build`／`up`／`down`／`bash` | `task docker:build`／`docker:up`／`docker:down`／`docker:bash` |
| `make build-pdf PAPER=<name>`／論文内の`make pdf` | `task compile:pdf paper=<name>` |
| `make build-docx PAPER=<name>`／論文内の`make docx` | `task compile:docx paper=<name>` |
| `make docx-review` | `task compile:docx paper=<name> format=review` |
| `make lint`／`review` | `task lint paper=<name>`／`task review paper=<name>` |
| `make word-templates` | `task compile:templates` |

```bash
task help
```

確認事項: Task定義が読み込めること。`format=review`の出力も`dist/main.docx`となる。
旧`all`はPDF・DOCXを順に実行する。旧`clean`に相当する削除タスクは提供しない。

## Phase 2: 論文別設定

### STEP 1: 設定値を転記する

`paper.mk`や論文内Makefileの値を`<PAPERS_DIR>/<paper>/paper.yml`へ転記する。
Make式は評価しない。キーは小文字、値は文字列にする。

```yaml
main_tex: main.tex
format: article
word_template: 0_Article_template.docx
skip_lint: '0'
```

確認事項: `MAIN_TEX`等を小文字キーへ対応付け、旧`common.mk`への参照を除くこと。
共有bibは`.env`の`BIB_DIR`、共有図は`figures/`を使用する。

### STEP 2: 出力を確認する

```bash
task compile:pdf paper=<name>
task compile:docx paper=<name>
```

確認事項: CLI指定 > 環境変数／`.env` > `paper.yml` > 既定値の順に適用されること。
