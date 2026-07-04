# mysdk-box (Ruby)

box API の読み取り系を扱う小さなクライアント。標準ライブラリ
(`net/http`, `json`)のみで実装している。

実装の設計解説と再実装の手引きは [docs/ruby.md](../docs/ruby.md) にある。

## 使い方

```ruby
require "mysdk-box"

client = MySdk::Box::Client.new(
  base_url: "https://example.com/api/v2",
  api_key: ENV["BOX_API_KEY"]
)

client.space                    # スペース情報
client.projects                 # プロジェクト一覧
client.project("DEMO")          # プロジェクト情報(ID またはキー)
client.issues                   # 課題一覧
client.issues(count: 20)        # クエリパラメータも渡せる
client.issue("DEMO-1")          # 課題情報
client.issue_comments("DEMO-1") # 課題コメント一覧
client.users                    # ユーザー一覧
client.statuses                 # 状態一覧
client.priorities               # 優先度一覧
```

戻り値はパース済みの JSON(`Hash` / `Array`)をそのまま返す。

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
export BOX_API_KEY=dummy-key
ruby example.rb
```

## ファイル構成

```text
lib/mysdk-box.rb            エントリポイント
lib/mysdk/box/client.rb     クライアント本体
lib/mysdk/box/errors.rb     エラー定義
example.rb                  実行サンプル
```
