# 開発環境

定義元: [pyproject.toml](../../../pyproject.toml)、[prek.toml](../../../prek.toml)。

ホストのuvでPython開発とテスト、go-taskで処理の起動を行う。
コンテナ内ではバインドマウントした`src/`を`PYTHONPATH`から読む。
依存関係とCLIエントリポイントを変更した場合はイメージを再ビルドする。

セットアップは[運用手順](../../operations/setup.md)、
テストコマンドは[AGENTS.md](../../../AGENTS.md)を参照。
