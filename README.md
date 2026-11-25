# drafter

LaTeX論文執筆環境とPythonユーティリティ。ホストで編集し、DockerでPDF・DOCX生成とAI校閲を実行する。

## ドキュメント

- [セットアップ（macOS／WSL）](docs/operations/setup.md)
- [リポジトリ構成](docs/architecture/overview.md)
- [Taskの配線・変数](tools/go-task/README.md)
- [図の生成](docs/operations/figures.md)
- [Makeからの移行](docs/operations/migration.md)
- [詳細仕様](SPEC.md)

## 基本コマンド

```bash
task help
task create:paper paper='日本語の 論文名'
task compile:pdf paper='日本語の 論文名'
task compile:docx paper='日本語の 論文名' format=short
task lint paper='日本語の 論文名'
task review paper='日本語の 論文名'
```

`uv run drafter --help`からPython CLIを直接利用できる。
`.tex`・`.pdf`・`.png`、論文・フォント・生成物はコミット対象外。
