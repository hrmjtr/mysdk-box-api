# mysdk-box

box API を利用するための、小さく分かりやすい API ライブラリ集。

本番利用向けの SDK ではなく、自分で実装する際の「動くドキュメント」
「リファレンス実装」として利用することを目的とする。
コードを読みながら API の使い方や実装パターンを理解できることを重視する。

## 構成

各言語は独立したディレクトリで管理する。実装間で機能・命名は揃えてある。

```text
ruby/     Ruby 実装(標準ライブラリのみ)
python/   Python 実装(標準ライブラリのみ)
go/       Go 実装(標準ライブラリのみ)
csharp/   C# 実装(.NET 8 / 標準ライブラリのみ)
mock/     サンプル実行用のモック API サーバー(Python)
docs/     再実装のためのドキュメント
```

各ディレクトリの README に、使い方とサンプルの実行方法を記載している。

## ドキュメント

自分で再実装するときは、次の順で読む。

1. [docs/api.md](docs/api.md) — box API の共通仕様(エンドポイント、データモデル、エラー分類)
2. 実装する言語の解説 — 設計の要点、再実装チェックリスト、拡張の指針
   - [docs/ruby.md](docs/ruby.md) — Ruby 実装の解説
   - [docs/python.md](docs/python.md) — Python 実装の解説(Ruby 経験者向け)
   - [docs/go.md](docs/go.md) — Go 実装の解説(Ruby 経験者向け)
   - [docs/csharp.md](docs/csharp.md) — C# 実装の解説(Ruby 経験者向け)

Python / Go / C# の解説は「Ruby との対応表」から始まり、
Ruby 実装との違いを軸に書いてある。

## 対応 API

読み取り系のみ。パスは `base_url` からの相対で統一している。

| 機能             | パス                       |
|------------------|----------------------------|
| スペース情報取得 | `GET /space`               |
| プロジェクト一覧 | `GET /projects`            |
| プロジェクト情報 | `GET /projects/{id}`       |
| 課題一覧         | `GET /issues`              |
| 課題情報         | `GET /issues/{id}`         |
| 課題コメント一覧 | `GET /issues/{id}/comments`|
| ユーザー一覧     | `GET /users`               |
| 状態一覧         | `GET /statuses`            |
| 優先度一覧       | `GET /priorities`          |

認証は API キーをクエリパラメータ `apiKey` で渡す方式。

## エラー処理

box API は HTTP 200 でも異常なレスポンス(空 Body、途中で切れた JSON、
壊れた JSON)を返す場合があるため、各実装で以下を区別して扱う。

| 種別             | 内容                                     |
|------------------|------------------------------------------|
| HTTP エラー      | ステータスコードが 2xx 以外              |
| 空レスポンス     | Body が空(または空白のみ)              |
| JSON パースエラー| JSON として解釈できない(壊れた JSON 等)|
| 想定外レスポンス | JSON としては正しいが、想定した形でない  |

エラー型の名前は言語ごとの慣習に合わせている(各言語の README を参照)。

## サンプルの動かし方

実 API がなくても動かせるように、モックサーバーを同梱している。

```sh
# ターミナル 1: モックサーバー起動(ポート 8793)
python3 mock/server.py

# ターミナル 2: 各言語のサンプルを実行
export BOX_BASE_URL=http://localhost:8793
export BOX_API_KEY=dummy-key

ruby ruby/example.rb
python3 python/example.py
(cd go && go run ./example)
(cd csharp && dotnet run --project Example)
```

モックサーバーには、エラー処理の動作確認用に壊れたエンドポイント
(`/broken/empty`, `/broken/truncated`, `/broken/http-error` など)も用意している。
