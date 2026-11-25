# review

定義元: [review.yml](review.yml)、[Python CLI](../../../src/drafter/cli.py)。

TeXを解析・分割し、章ルールとともにOpenAI互換APIへ送り、dist/review-report.mdへ保存する。

| 入口 | 呼び出し | 処理本体 |
|---|---|---|
| `review paper=...` | `uv run drafter review --paper ...` | `reviewer.pipeline.run` |

[フロー図の編集元](diagrams/flow.drawio)

![reviewの実行フロー](diagrams/flow.svg)

## 入力

- paper: 論文名（必須）
- main_tex: 入力名（既定main.tex）

論文設定はCLI > 環境変数／`.env` > `paper.yml` > 既定値の順。
lint失敗・外部ツール失敗は終了コードで呼び出し元へ返す。

[Task一覧へ戻る](../README.md)
