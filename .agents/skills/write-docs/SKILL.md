---
name: write-docs
description: リポジトリのドキュメント（構成・運用・データモデル・API・図）と、draw.ioによる構成図・モジュール依存図・アクティビティ図・ER図を新規作成・分割・更新するときの規約。固定のディレクトリ構成を持たず、TypeScript・Python・Go等の技術スタックとリポジトリの特性（Webアプリ・API・ライブラリ・CLI・IaC・monorepo）を事前に確認し、作る種別・置き場所・図のツールを決める。
---

# /write-docs — ドキュメント作成規約（汎用）

固定の構成表を持たない。書き始める前に、下の「事前確認」でリポジトリの実態を確認し、その結果から**作る種別（§2）・置き場所（§3）・図のツール（§5）**を決める。リポジトリに既存の規約（`CLAUDE.md`・`AGENTS.md`・`docs/README.md`・既存の配置）がある場合はそちらを優先する。

## 1. 事前確認

ファイルを開く・コマンドを実行して確認する。結果は事実として扱い、確認できないことは書かない。

| 確認したいこと | 確認方法 | 結果の使い道 |
|---|---|---|
| 何で作られているか（言語・基盤） | 設定ファイルの有無を見る: `package.json`、`pyproject.toml` / `requirements.txt`、`go.mod`、`Cargo.toml`、`*.tf`、`docker-compose.yml`、k8sマニフェスト | 定義元の種類（下の行）と、運用コマンドの書き方を決める |
| 何のリポジトリか | READMEと主要ディレクトリを読み、Webアプリ / API / ライブラリ / CLI / バッチ・データ・ML / IaC のどれか（複数可）を判断する | §2で作る種別（フォルダ）を選ぶ |
| どんな部品（コンポーネント）があるか | ディレクトリ構成（`apps/*`・`packages/*`・`backend/` + `frontend/`）、`package.json` の `workspaces`、composeの `services`、terraformのモジュールを見る | §3でディレクトリを何個切るか決める |
| 環境ごとに構成が違うか | dev / staging / prod の設定ファイル・IaCを見比べる | 別物なら環境ごとにファイルを分け、設定値の違いだけなら比較表にする |
| すでにドキュメントがあるか | `docs/`、各 `README.md`、索引、`CLAUDE.md` / `AGENTS.md` を読む。配置・命名・言語（日本語/英語）を控える | 既存の形に合わせる。重複して作らない |
| 情報の元（定義元）はどこか | DBスキーマ（Prisma / SQLAlchemy / Alembic / Django models / SQLマイグレーション）、API定義（OpenAPI / proto / ルート定義）、CLI定義（argparse / click / commander）、IaCを探す | 定義元がある情報は複製せず、リンクと補足だけにする |
| 使える図のツールは何か | `which drawio plantuml dot mmdc` を実行し、既存の図の拡張子（`.drawio` / `.puml` / `.mmd`）も見る | §5でツールを決める |

確認後、次の3点を書き出してから作業に入る（ユーザーに示してよい）。
1. 作る種別（§2）
2. 置き場所と構成（§3）
3. 図のツール（§5）

## 2. 作る種別（フォルダ）を選ぶ

種別ごとに**フォルダ**を切り、配下に topic 単位でファイルを置く。1つの `.md` に種別全体を書かない。該当する種別だけ作る。

| フォルダ | 作る条件 | 配下のファイル（topic単位の例） | 定義元の例 |
|---|---|---|---|
| `architecture/` | 複数コンポーネント・複数環境がある | `overview.md`（構成図・環境比較）、`connection.md`（接続設計）など設計の論点ごと | compose、IaC |
| `operations/` | コマンド・デプロイ・障害対応がある | `setup.md`、`commands.md`、`deploy.md`、`troubleshooting.md` | Makefile、CI |
| `data-model/` | DB・永続化がある | `er.md`（ER図・オブジェクト一覧）、`tables/<テーブル名>.md`（列・型・NULL・制約・説明・業務ルール） | Prisma、SQLAlchemy、Alembic、SQL |
| `api/` | HTTP API・公開API・CLIがある | リソース（または機能群）ごとに `<resource>.md`、`errors.md` | OpenAPI、ルート定義、argparse |
| `configuration/` | 環境変数・設定ファイルが多い | `env-vars.md`、`<設定ファイル>.md`（名前・既定値・必須か・意味） | `.env.example`、設定クラス |
| `testing/` | 実DBなど特殊なテスト環境がある | `strategy.md`、`isolation.md`、`running.md` | テスト設定 |

- 各フォルダに `README.md`（そのフォルダの概要と索引）を置く。
- 設計判断（選択肢・採否の経緯）は Issue などコード外に起票する。docs には決定した結果（現在の設計）と、設定値の理由だけを書く。経緯を書くための `decisions/` は作らない。
- 1ファイル=1 topic。対象が複数ある種別（テーブル、エンドポイント、コンテナなど）は**対象ごとにファイルを分ける**。
- 内容が少ないうちも、フォルダは切る。最初は `README.md` と必要なファイルだけでよい。
- 定義元がある種別は、冒頭に定義元を明記する。複製は最小にする。
- 各フォルダの `README.md` には、そのフォルダの概要と索引だけを書く。「更新」節は置かない（履歴はgit、更新の規則は§8が持つ）。

## 3. 配置を決める

`docs/<コンポーネント>/<種別>/<topic>.md` を基本にする。

- 単一コンポーネント: `docs/<種別>/`
- monorepo: `docs/<component>/<種別>/` またはパッケージ内の `docs/`（リポジトリの慣習に合わせる）
- 全体構成図とcomponent間の関係は `docs/architecture/overview.md`、モジュール配置は `docs/architecture/<component>/modules.md` に記載する。
- 各componentに `development.md` と `production.md` を置く。環境ごとの違いを記載し、同じ部分は「developmentと同じ」等と明記して該当箇所へリンクする。
- **構成**（`architecture/`）と**運用**（`operations/`）は別フォルダにする。1ファイルに異なる粒度（設計とコマンド）を同居させない。
- 各componentの `modules.md` にモジュール構成図と依存関係表を載せる。図は同じcomponentの `diagrams/modules.drawio` と `diagrams/modules.svg` に置く。
- 矢印は依存元から依存先へ向け、呼び出し・型/スキーマ参照・コード生成・通信・設定参照などの関係をラベルで示す。実行時と生成/初期化時を区別し、根拠となるソースや設定へリンクする。未実装は計画と明記する。
- 移動・削除したらリンク元と索引（各 `README.md`、`docs/README.md`）を更新する。

例:

```text
# Next.js + Prisma + Docker + AWS
docs/architecture/
  README.md  overview.md
  application/  README.md  modules.md  development.md  production.md
  database/     README.md  modules.md  development.md  production.md  connection.md
  tailscale/    README.md  modules.md  development.md  production.md
  diagrams/
docs/database/
  README.md
  data-model/   er.md  tables/account.md  tables/category.md ...
  operations/   commands.md  troubleshooting.md
  diagrams/
docs/operations/
  README.md  development/  production/
docs/testing/
  README.md  isolation.md  running.md

# Python API（FastAPI + SQLAlchemy + Alembic）
docs/
  api/            users.md  orders.md  errors.md
  data-model/     er.md  tables/user.md ...   # 定義元は SQLAlchemy モデル
  operations/     setup.md  migration.md
  architecture/   overview.md

# Pythonライブラリ
docs/
  architecture/   overview.md
  api/            <公開モジュールごと>.md
  testing/        strategy.md

# Terraform
docs/<module>/
  architecture/   overview.md
  operations/     apply.md  troubleshooting.md
```

## 4. 項目の粒度を揃える

- 同じ階層・同種の対象（コンテナ、環境、テーブル、エンドポイントなど）は**同じ項目セット**で書く。
- 対象が複数なら比較表にする。項目を行、対象を列にする。
- 該当しない項目は「なし」、元の情報にないものは「未確定」と書く。推測で埋めない。
- 全対象に共通する事項は上位（共通表・注意書き）に1回だけ書く。
- 項目名・順序・文の形式も揃える。
- 同じ階層の箇条書きは、同じ形式・同じ粒度にする。「項目名: 説明」に統一する、または全項目を文（名詞句）に統一する。
- 同じ階層に、1語の項目と複数文の項目を混在させない。長い説明は文を絞るか、表にする。
- 同じ階層に、子項目のある項目と無い項目を混在させない。子項目は親の説明に統合するか、全項目に揃える。
- 1つの項目に複数の事柄を詰め込まない。事柄ごとに項目を分ける。

## 5. 図

### 図の種類とツール

| 図 | 用途・記載内容 | ツール |
|---|---|---|
| 構成図 | 全体のcomponent・配置・接続、component内のモジュールと依存関係 | draw.io（`.drawio` + `.svg`） |
| アクティビティ図 | 業務処理・API処理・運用手順の順序、条件分岐、並行処理、異常系 | draw.io（`.drawio` + `.svg`） |
| ER図 | エンティティ、主キー・外部キー、関連の多重度・任意性 | draw.io（`.drawio` + `.svg`） |

- 構成図・アクティビティ図・ER図はdraw.ioで作成・更新する。既存の別形式の図は、変更対象でなければ一括変換しない。
- 図は対象componentの`diagrams/`に置き、説明するMarkdownから画像と編集元を相対リンクする。全体構成図は`architecture/overview.md`、モジュール構成図はcomponentの`modules.md`に載せる。
- アクティビティ図は処理単位の`<topic>-activity.drawio`と`.svg`に分け、対応する仕様・設計・運用文書に載せる。単純な処理を無理に図にしない。
- ツールが無い場合は導入可否を確認する。導入できない場合はMermaidを代替とし、理由を報告する。

### フロー図の表記と配置

- 処理の各段階は「TeXを整形する」「成果物を保存する」のように動詞で表す。フローの処理ノードを機能名・名詞だけにしない。
- 原則として日本語を使う。CLI・Docker・Pandoc、コマンド・ファイル名など、英語の方が識別しやすい表記は残す。判断は「利用できるか」等の問いにし、分岐も「はい」「いいえ」等の日本語で記す。
- このリポジトリのTaskの配線・フロー図は`tools/go-task/<task>/README.md`に置く。定義元のYAML・呼び出すCLI・処理本体を対応付け、`tools/go-task/README.md`は索引にする。リポジトリ全体の構成は`docs/architecture/`に分ける。
- 各Taskの編集元は`diagrams/flow.drawio`、掲載画像は`diagrams/flow.svg`とし、READMEにSVGプレビューと編集元リンクを載せる。画像の書き出しやリンクだけで済ませず、Markdownに画像として埋め込む。
- 長い日本語はノード内で改行する。矢印の接続位置・経由点を指定し、ノードや文字を横切らないようにする。PNG等で実際に表示し、文字切れ・ラベルの重なり・矢印の方向・分岐条件を確認してから完了にする。

### 内容・表記

- 構成図の矢印には、呼び出し・通信・型参照・生成などの関係を付記する。実行時の依存と生成・初期化時の依存を区別する。
- ER図はスキーマを定義元にし、主キー（PK）・外部キー（FK）・主要列を記載する。関連はCrow's Foot表記で多重度と任意性を示し、NULL可否・一意制約と整合させる。編集元は`diagrams/er.drawio`、書き出しは`diagrams/er.svg`とし、`data-model/er.md`から参照する。
- アクティビティ図は開始・終了、処理、判断・合流を使い、分岐に条件を明記する。並行処理がある場合のみフォーク・ジョイン、担当が分かれる場合のみスイムレーンを使う。
- 正常系と主要な異常系を、実装・仕様で確認できる範囲で示す。未実装の流れは計画と明記し、根拠となるソース・設定へリンクする。
- 設定値（タイムアウト等）は図に載せず表に書く。同じ図は複製せず相対リンクで再利用する。ASCIIアートは使わない。
- draw.ioの「Format → Diagram → Background」は白（`#FFFFFF`）にする。XMLでは`mxGraphModel`の`background="#FFFFFF"`に相当する。

### 書き出し・確認

編集元とSVGの両方を保存・コミットする。SVGはライトテーマ固定で書き出し、ダークモードで背景・文字色が自動反転しないようにする。

```bash
drawio -x -f svg --svg-theme light --embed-svg-fonts false -o <name>.svg <name>.drawio
drawio -x -f png -o <preview>.png <name>.drawio
```

- AWSリソースはdraw.ioの標準アイコン`mxgraph.aws4.*`を使う。
- PNGを目視し、文字切れ・矢印の重なり・依存方向・分岐条件を確認する。SVGの背景が白、テーマがlightであることも確認する。
- 図の直前に編集元へのリンクを置く。書き出しコマンドは下の「書き出し・確認」に従い、READMEには書かない。確認用PNGは必要がなければコミットしない。

## 6. 記述ルール

- docsは最新の設計・手順・条件を書くストック情報。設計の前提になる情報だけを選んで載せる。
- 載せる情報と載せない情報を、次の表で判断する。

| 区分 | 載せる（ストック） | 載せない（フロー。Issue・PRに書く） |
|---|---|---|
| 設計・条件 | 現在の設計、満たすべき条件、設定値とその理由 | 設計判断の経緯、選択肢の比較 |
| 手順 | 最新の手順、コマンド | 実施した日付、実施者、実施履歴 |
| 状態 | 「計画」「未決」「未確定」の区別 | 進捗（作成中・未実施・完了・対応済み）、実装状況の記録 |
| 数値 | 設計値、上限、しきい値 | 実測値・検証結果（サイズ、digest、所要時間、テスト件数） |
| 履歴 | なし（履歴はgitのcommitとPRが持つ） | 更新履歴、変更履歴、日付 |

- 検証結果は、docsではなくIssue・PRに書く。そこから「満たすべき条件」だけを、日付・結果を含めずにdocsへ整理する。
- Issue / PR番号・Issue名を書かない。未整備のことは「今後整備する」と書く。
- 手順書（`operations/`のセットアップ・検証・デプロイ・復旧など）は、Phase > STEP構成で書く。Phaseは目的ごとの大区分、STEPはPhase内の実行順の作業とする。各STEPにコマンドと確認事項を置き、Phase・STEPの見出しは番号付きにする。前提・信頼境界など手順外の注意は、末尾の独立節にまとめる。
- 手順書は、処理の順序・条件分岐・異常系がある手順にフロー図（§5のアクティビティ図）を載せる。図は該当STEPの直下に置き、Phase・STEPの順序と対応させる。フロー図は概念（主要な段階と分岐）に絞り、コマンド名・回数・パスなどの詳細は書かない。図の近くに正本（コード）へのリンクを置き、詳細はコードを正とする。手順全体（全Phase）の流れを示す図は文書の冒頭（Phase一覧の直後）に置き、個別の処理の図は該当STEPの直下に置く。図が不要なのは単純な1〜2コマンドの手順だけ。
- 簡潔・高密度に書き、物語調にしない。言語はリポジトリの既存ドキュメントに合わせる。
- 実装と一致することを、コードや設定を開いて確認してから書く。
- 文書はDRYにする。同じ事実・表・説明を複数の文書に書かず、1か所（管理元）に書いて、他はリンクで参照する。repoをまたぐ場合も同じ。
- 定義元（コード・設定・IaC・他の文書）がある情報は、定義元へのリンクと補足だけにする。
- 図は、利用側の文書で繰り返し載せてよい。ただし編集元は1つにし、同じ図の複製を作らない（相対リンクで再利用する）。

## 7. 完了前の確認

同梱のスクリプトを実行する（このskillのディレクトリの `scripts/check_docs.py`）。

```bash
python3 <skillのディレクトリ>/scripts/check_docs.py docs [--exclude docs/features]
```

| チェック | 内容 |
|---|---|
| リンク切れ | Markdownの相対リンク・画像リンク |
| Issue / PR番号 | `#12`、`issues/12` などの混入（§6） |
| 書き出し漏れ | `.drawio` / `.puml` / `.mmd` に対応する `.svg` がない |
| README | `.md` を含む各フォルダに `README.md` がない |

- 問題があれば一覧が出て、終了コード1で終わる。直して再実行し、「問題なし」になるまで繰り返す。
- スクリプトで確認できないこと（実装との一致、項目の粒度、図の見た目）は、§4・§5・§6 に従って手で確認する。
- 旧パスの参照は `grep` で確認する（移動・削除したとき）。

## 8. 更新

ドキュメントは、定義元（コード・設定・IaC）が変わったら同じ変更で更新する。更新対象の表はREADMEに置かず、次の手順で決める。

1. 変更の差分から影響する定義元を特定し、その定義元を参照しているドキュメントを `grep` で探して更新対象にする。
2. 該当ファイルだけを更新する。ファイルを開き、実装と一致していることを確認してから書く（記述と実装が食い違うときは、実装を正とする）。
3. 図は**編集元**（`.drawio` / `.puml`）を更新し、書き出し（§5）を再実行して、編集元と `.svg` を一緒にコミットする。
4. ファイルを移動・削除・追加したら、リンク元・索引（各 `README.md`、`docs/README.md`）と旧パスの参照（`grep`）を更新する。
5. §7 の確認を実行する。
6. コードの変更と同じPRでドキュメントを更新する。後回しにしない。

### 乖離を見つけたとき

- 実装と食い違うドキュメントを見つけたら、依頼の範囲内なら直す。範囲外なら、直す箇所を報告する。
