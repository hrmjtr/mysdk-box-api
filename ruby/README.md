# mysdk-box (Ruby)

Box API の読み取り系を扱う小さなクライアント。標準ライブラリ
(`net/http`, `json`)のみで実装している。

ドキュメント(Ruby をほとんど知らない人でも読める):

- [docs/01-setup.md](docs/01-setup.md) — 環境構築と最小限の言語入門
- [docs/02-implementation.md](docs/02-implementation.md) — 実装の設計解説
- [docs/03-reimplement.md](docs/03-reimplement.md) — ステップバイステップ再実装ガイド

## 使い方

```ruby
require "mysdk-box"

client = MySdk::Box::Client.new(
  base_url: "https://api.box.com/2.0",
  access_token: ENV["BOX_ACCESS_TOKEN"]
)

client.current_user                     # 現在のユーザー情報
client.user("1")                        # ユーザー情報
client.folder("0")                      # フォルダ情報("0" はルート)
client.folder_items("0")                # フォルダ内アイテム一覧
client.folder_items("0", limit: 10)     # クエリパラメータも渡せる
client.folder_collaborations("11")      # コラボレーション一覧
client.file("101")                      # ファイル情報
client.file_comments("101")             # ファイルコメント一覧
client.search("report")                 # 検索
```

戻り値はパース済みの JSON(`Hash`)をそのまま返す。
一覧系はコレクション形式なので、要素は `["entries"]` で取り出す。

```ruby
client.folder_items("0")["entries"].each do |item|
  puts "#{item["type"]}: #{item["name"]}"
end
```

## エラー

すべて `MySdk::Box::Error` を継承している。

| クラス                    | 意味                             |
|---------------------------|----------------------------------|
| `HttpError`               | 2xx 以外(`#status` `#body` 参照)|
| `EmptyResponseError`      | 200 だが Body が空               |
| `ParseError`              | JSON として解釈できない          |
| `UnexpectedResponseError` | JSON だが想定した形でない        |

## サンプルの実行

リポジトリルートでモックサーバーを起動してから実行する。

```sh
python3 ../mock/server.py &

export BOX_BASE_URL=http://localhost:8793
export BOX_ACCESS_TOKEN=dummy-token
ruby example.rb
```

実際の Box API に対しては `BOX_BASE_URL` を外し、
`BOX_ACCESS_TOKEN` に Developer Token を設定する。

## ファイル構成

```text
lib/mysdk-box.rb            エントリポイント
lib/mysdk/box/client.rb     クライアント本体
lib/mysdk/box/errors.rb     エラー定義
example.rb                  実行サンプル
```
