# mysdk-box (Python)

Box API の読み取り系を扱う小さなクライアント。標準ライブラリ
(`urllib`, `json`)のみで実装している。

実装の設計解説と再実装の手引き(Ruby 経験者向け)は
[docs/python.md](../docs/python.md) にある。

## 使い方

```python
import os
from mysdk_box import Client

client = Client(
    base_url="https://api.box.com/2.0",
    access_token=os.environ["BOX_ACCESS_TOKEN"],
)

client.current_user()                   # 現在のユーザー情報
client.user("1")                        # ユーザー情報
client.folder("0")                      # フォルダ情報("0" はルート)
client.folder_items("0")                # フォルダ内アイテム一覧
client.folder_items("0", limit=10)      # クエリパラメータも渡せる
client.folder_collaborations("11")      # コラボレーション一覧
client.file("101")                      # ファイル情報
client.file_comments("101")             # ファイルコメント一覧
client.search("report")                 # 検索
```

戻り値はパース済みの JSON(`dict`)をそのまま返す。
一覧系はコレクション形式なので、要素は `["entries"]` で取り出す。

```python
for item in client.folder_items("0")["entries"]:
    print(f"{item['type']}: {item['name']}")
```

## エラー

すべて `mysdk_box.BoxError` を継承している。

| クラス                    | 意味                             |
|---------------------------|----------------------------------|
| `HttpError`               | 2xx 以外(`.status` `.body` 参照)|
| `EmptyResponseError`      | 200 だが Body が空               |
| `ParseError`              | JSON として解釈できない          |
| `UnexpectedResponseError` | JSON だが想定した形でない        |

## サンプルの実行

リポジトリルートでモックサーバーを起動してから実行する。

```sh
python3 ../mock/server.py &

export BOX_BASE_URL=http://localhost:8793
export BOX_ACCESS_TOKEN=dummy-token
python3 example.py
```

実際の Box API に対しては `BOX_BASE_URL` を外し、
`BOX_ACCESS_TOKEN` に Developer Token を設定する。

## ファイル構成

```text
mysdk_box/__init__.py   エントリポイント
mysdk_box/client.py     クライアント本体
mysdk_box/errors.py     エラー定義
example.py              実行サンプル
```
