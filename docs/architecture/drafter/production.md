# 成果物生成環境

定義元: [Dockerfile](../../../Dockerfile)、[Compose](../../../docker-compose.yml)。

常駐サービスの本番デプロイは持たない。成果物生成は
[開発環境](development.md)と同じComposeサービスを使う。
論文ごとの`dist/`へPDF・DOCX・校閲レポートを出力する。
フォントはホストから読み取り専用で供給し、イメージに含めない。
