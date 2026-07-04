# mysdk-box (Python)

box API の読み取り系を扱う小さなクライアント。標準ライブラリ
(`urllib`, `json`)のみで実装している。

実装の設計解説と再実装の手引き(Ruby 経験者向け)は
[docs/python.md](../docs/python.md) にある。

## 使い方

```python
from mysdk_box import Client

client = Client(
    base_url="https://example.com/api/v2",
    api_key=os.environ["BOX_API_KEY"],
)

client.space()                    # スペース情報
client.projects()                 # プロジェクト一覧
client.project("DEMO")            # プロジェクト情報(ID またはキー)
client.issues()                   # 課題一覧
client.issues(count=20)           # クエリパラメータも渡せる
client.issue("DEMO-1")            # 課題情報
client.issue_comments("DEMO-1")   # 課題コメント一覧
client.users()                    # ユーザー一覧
client.statuses()                 # 状態一覧
client.priorities()               # 優先度一覧
```

戻り値はパース済みの JSON(`dict` / `list`)をそのまま返す。

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
export BOX_API_KEY=dummy-key
python3 example.py
```

## ファイル構成

```text
mysdk_box/__init__.py   エントリポイント
mysdk_box/client.py     クライアント本体
mysdk_box/errors.py     エラー定義
example.py              実行サンプル
```
