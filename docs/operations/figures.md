# 図の生成

定義元: [図生成処理](../../src/drafter/figures.py)、
[Task定義](../../tools/go-task/generate/generate.yml)。

## Phase 1: ソースの準備

### STEP 1: 使うツールを確認する

| mode | 必要なツール | 出力設定 |
|---|---|---|
| `drawio` | draw.io Desktopの`drawio` | 各ページのデータ`output` |
| `mermaid` | Mermaid CLIの`mmdc` | `%% output: filename.svg` |
| `plantuml` | PlantUMLの`plantuml` | `' output: filename.svg` |
| `python` | uv | Pythonコードの保存先指定 |

ホストへ事前導入し、PATHから起動できることを前提とする。setupでは検証・導入しない。
[draw.io Desktop](https://github.com/jgraph/drawio-desktop)、
[Mermaid CLI](https://github.com/mermaid-js/mermaid-cli)、
[PlantUML](https://plantuml.com/command-line)の導入手順を参照する。
Mermaid CLIはNode.js環境で`npm install -g @mermaid-js/mermaid-cli`により導入する。
WSLのdraw.io DesktopにはLinux GUI実行環境（WSLg等）が必要。

### STEP 2: 出力名をソースに設定する

入力は`figures/`配下に置く。Taskには入力パスだけを指定する。
出力先はソースファイルのディレクトリからの相対パスで、SVG／PNG／PDFを指定する。

draw.ioは何も選択していない状態でDiagramのEdit Dataを開き、`output`を追加する。
複数ページでは各ページに異なる出力名を指定する。圧縮XMLも読み込める。

Mermaidの例:

```text
%% output: flow.svg
flowchart LR
  A --> B
```

Pythonの例:

```python
from pathlib import Path
import matplotlib.pyplot as plt

plt.plot([0, 1], [0, 1])
plt.savefig(Path(__file__).with_name('plot.svg'))
```

確認事項: Pythonはコードで出力名・形式を決める。依存は必要に応じてPEP 723形式で宣言する。

## Phase 2: 生成

### STEP 1: モードと入力を指定する

```bash
task generate:fig path=figures/model/model.drawio
task generate:fig:drawio path=figures/model/model.drawio
task generate:fig:mermaid path=figures/flow/flow.mmd
task generate:fig:python path=figures/plot/plot.py
task generate:fig:plantuml path=figures/model/model.puml
```

確認事項: ソース内の指定どおりにファイルが出力されること。
直接実行は`uv run drafter generate-figure --path <path>`。
拡張子で自動判別し、`--mode`で明示指定できる。PlantUMLの出力指定は単一行コメントに書く。
Pythonはソースのディレクトリを作業ディレクトリとして実行する。
draw.io／Mermaid／PlantUMLの出力は`figures/`配下に限定する。
