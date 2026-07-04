# mysdk-box

> [!IMPORTANT]
> このリポジトリは [hrmjtr/etudes](https://github.com/hrmjtr/etudes) の `box/` に移行し、アーカイブされた。

Box API(box.com / Box Platform REST API)を利用するための、
小さく分かりやすい API ライブラリ集。

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

共通ドキュメント(`docs/`):

- [docs/api.md](docs/api.md) — Box API の共通仕様(エンドポイント、データモデル、エラー分類)
- [docs/roadmap.md](docs/roadmap.md) — 再実装ロードマップ(ステップの順序と各ステップの完了条件)

言語別ドキュメント(各言語の `docs/` 内)。
**その言語をほとんど触ったことがないエンジニア**でも進められるように書いてある。

| 言語   | 01 環境構築 + 言語入門 | 02 実装解説 | 03 再実装ガイド |
|--------|------------------------|-------------|-----------------|
| Ruby   | [ruby/docs/01-setup.md](ruby/docs/01-setup.md) | [02-implementation.md](ruby/docs/02-implementation.md) | [03-reimplement.md](ruby/docs/03-reimplement.md) |
| Python | [python/docs/01-setup.md](python/docs/01-setup.md) | [02-implementation.md](python/docs/02-implementation.md) | [03-reimplement.md](python/docs/03-reimplement.md) |
| Go     | [go/docs/01-setup.md](go/docs/01-setup.md) | [02-implementation.md](go/docs/02-implementation.md) | [03-reimplement.md](go/docs/03-reimplement.md) |
| C#     | [csharp/docs/01-setup.md](csharp/docs/01-setup.md) | [02-implementation.md](csharp/docs/02-implementation.md) | [03-reimplement.md](csharp/docs/03-reimplement.md) |

読む順番:

1. `docs/api.md` で API を理解する
2. 実装する言語の `01-setup.md` で環境と最小限の文法を押さえる
3. `02-implementation.md` でこのリポジトリの実装を読み解く
4. `docs/roadmap.md` と `03-reimplement.md` に沿って、ステップバイステップで自分の手で再実装する

## 対応 API

読み取り系のみ。パスは `base_url`(通常 `https://api.box.com/2.0`)からの相対で統一している。

| 機能                   | パス                               |
|------------------------|------------------------------------|
| 現在のユーザー情報     | `GET /users/me`                    |
| ユーザー情報           | `GET /users/{id}`                  |
| フォルダ情報           | `GET /folders/{id}`                |
| フォルダ内アイテム一覧 | `GET /folders/{id}/items`          |
| コラボレーション一覧   | `GET /folders/{id}/collaborations` |
| ファイル情報           | `GET /files/{id}`                  |
| ファイルコメント一覧   | `GET /files/{id}/comments`         |
| 検索                   | `GET /search?query=...`            |

認証はアクセストークンを `Authorization: Bearer <token>` ヘッダーで渡す方式。

## エラー処理

HTTP 200 でも異常なレスポンス(空 Body、途中で切れた JSON、壊れた JSON)が
返る場合を想定し、各実装で以下を区別して扱う。

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
export BOX_ACCESS_TOKEN=dummy-token

ruby ruby/example.rb
python3 python/example.py
(cd go && go run ./example)
(cd csharp && dotnet run --project Example)
```

実際の Box API に対して動かす場合は、`BOX_BASE_URL` を外し
(デフォルトで `https://api.box.com/2.0` が使われる)、
`BOX_ACCESS_TOKEN` に開発者コンソールで発行した Developer Token を設定する。

モックサーバーには、エラー処理の動作確認用に壊れたエンドポイント
(`/broken/empty`, `/broken/truncated`, `/broken/http-error` など)も用意している。
