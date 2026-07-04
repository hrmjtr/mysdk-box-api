# Python 実装の解説(Ruby 経験者向け)

`python/` 以下の実装を、Ruby 実装([ruby.md](ruby.md))との対比で解説する。
API 仕様は [api.md](api.md) を先に読むこと。

## Ruby との対応表

| Ruby                          | Python                        | 備考 |
|-------------------------------|-------------------------------|------|
| `module MySdk::Box`           | パッケージ `mysdk_box/`       | Python の名前空間はディレクトリ |
| `require`                     | `import` / `from ... import`  | |
| `lib/mysdk-box.rb`(入口)    | `mysdk_box/__init__.py`       | 公開 API の re-export を書く |
| `StandardError`               | `Exception`                   | |
| `rescue XxxError => e`        | `except XxxError as e:`       | |
| `raise X, "msg"`              | `raise X("msg")`              | |
| `Net::HTTP`                   | `urllib.request`              | どちらも標準ライブラリ |
| `JSON.parse`                  | `json.loads`                  | |
| `Hash` / `Array`              | `dict` / `list`               | |
| `nil`                         | `None`                        | |
| `hash["key"]`                 | `dict["key"]`(`KeyError`)   | Ruby は無いキーで `nil`、Python は例外 |
| `hash.dig("a", "b")`          | `d.get("a", {}).get("b")`     | 直接の対応物はない |
| キーワード引数 `params = {}`  | `**params`                    | `folder_items("0", limit=10)` と書ける |
| `@base_url`                   | `self.base_url`               | Python に private 変数の強制はない |
| private メソッド              | `_get` のような `_` 接頭辞    | 慣習であって強制ではない |

## ファイル構成と読む順番

```text
python/
├── mysdk_box/
│   ├── __init__.py     # 1. エントリポイント(公開名の re-export)
│   ├── errors.py       # 2. エラー定義
│   └── client.py       # 3. クライアント本体
└── example.py          # 4. 利用例とエラーハンドリングの見本
```

`__init__.py` で `Client` とエラー群を re-export しているため、
利用側は `from mysdk_box import Client, HttpError` とパッケージ名だけで書ける。
Ruby で `require "mysdk-box"` 1 本で全部読めるようにするのと同じ発想。

## 設計の要点

### 1. クライアントの形は Ruby 版と同じ

```python
class Client:
    def __init__(self, base_url, access_token):
        self.base_url = base_url.rstrip("/")   # Ruby の chomp("/") 相当
        self.access_token = access_token

    def folder(self, folder_id):
        return self._get(f"/folders/{folder_id}")

    def folder_items(self, folder_id, **params):
        return self._get(f"/folders/{folder_id}/items", params)
```

- Ruby の endless method のような 1 行定義はないので、通常の 2 行メソッド。
- `folder_items("0", limit=10)` のようにキーワード引数がそのまま
  クエリパラメータになる。Ruby 版の `folder_items("0", limit: 10)` と同じ使い勝手。
- `file` という組み込み関数を潰す名前を避けたい場合は `file_info` などに
  変えてもよいが、Python 3 では `file` は組み込みではないため実害はない。

### 2. リクエスト:ヘッダー付きは Request オブジェクトを作る

```python
def _get(self, path, params=None):
    url = f"{self.base_url}{path}"
    if params:
        url += f"?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {self.access_token}"}
    )

    try:
        with urllib.request.urlopen(request) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise HttpError(e.code, e.read().decode("utf-8", "replace")) from e

    return self._parse(body)
```

- `urlopen(url)` に直接ヘッダーは渡せないため、`urllib.request.Request` に
  URL とヘッダーを詰めてから `urlopen` する。Ruby の
  `Net::HTTP.get_response(uri, headers)` に相当する 2 段構え。

**ここが Ruby と挙動が逆になる要注意ポイント:**

- Ruby の `Net::HTTP` は非 2xx でも普通にレスポンスを返す(自分で判定する)。
- Python の `urllib.request.urlopen` は **非 2xx で `HTTPError` 例外を投げる**。
  そのため「ステータスコード判定」は if 文ではなく except 節に現れる。
  例外オブジェクト自体がレスポンスを兼ねており、`e.code` と `e.read()` で
  ステータスと Body を取り出して自前の `HttpError` に詰め替える。

その他:

- `urllib.parse.urlencode` = Ruby の `URI.encode_www_form`。
- `with ... as response:` = Ruby のブロック付き `File.open` と同じ確実クローズ。
- `raise ... from e` は例外の因果関係を残す書き方(Ruby の `cause` は自動、
  Python は明示する)。
- `body` は bytes で届くので `decode("utf-8")` が必要。Ruby の String と違い
  Python は文字列とバイト列が別型。

### 3. レスポンス判定は Ruby 版と同一ロジック

```python
def _parse(self, body):
    if not body.strip():                                   # [2] 空レスポンス
        raise EmptyResponseError("response body is empty")
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:                      # [3] パースエラー
        raise ParseError(f"failed to parse JSON: {e}") from e
    if not isinstance(data, (dict, list)):                 # [4] 想定外
        raise UnexpectedResponseError(...)
    return data
```

- `isinstance(data, (dict, list))` = Ruby の `data.is_a?(Hash) || data.is_a?(Array)`。
- [1] HTTP エラーだけは前述の通り `_get` 側(except 節)で処理される。
  判定フローの順序自体は api.md と同じ。

### 4. エラー階層

```python
class BoxError(Exception): ...          # 基底(Ruby の Error < StandardError)

class HttpError(BoxError):              # [1] .status / .body を保持
class EmptyResponseError(BoxError):     # [2]
class ParseError(BoxError):             # [3]
class UnexpectedResponseError(BoxError): # [4]
```

Ruby と同じ「基底 1 つ + 4 分類」。`except BoxError` で一括捕捉できる。
Python では docstring がクラスの説明を兼ねる(`help()` で見える)。

### 5. 戻り値は素の dict / list

Ruby 版と同じ方針。キーは文字列(snake_case のまま)。
一覧系はコレクション形式のまま返すので、要素は `["entries"]` で取り出す。
Ruby と違って `dict["ないキー"]` は `KeyError` 例外になるため、
無いかもしれないキーは `folder.get("created_at")` を使う
(ルートフォルダの `created_at` は `None`)。

## 動かし方

```sh
python3 mock/server.py &                  # リポジトリルートで

export BOX_BASE_URL=http://localhost:8793
export BOX_ACCESS_TOKEN=dummy-token
python3 python/example.py
```

`example.py` と `mysdk_box/` が同じディレクトリにあるため、
そのまま import が通る(pip install は不要)。

## 再実装チェックリスト

1. `errors.py`: 基底 + 4 分類のエラークラス
2. `client.py`: `_get` で URL 組み立て(`urlencode`)と
   `Request` + Authorization ヘッダー
3. `urlopen` を try/except で囲み、`HTTPError` を自前の型に詰め替える
4. `_parse`: 空 Body → `json.loads` → `isinstance` の順で判定
5. `__init__.py` で公開名を re-export
6. モックサーバーの `/broken/*` 5 種で分類が正しいことを確認する

## 拡張の指針(本リポジトリではやらないこと)

- **タイムアウト**: `urlopen(request, timeout=10)` で指定できる(Ruby 版より簡単)。
- **requests / httpx の採用**: 実務では標準の urllib より
  `requests` が一般的。その場合 `response.raise_for_status()` が
  分類 [1] に、`response.json()` の `JSONDecodeError` が [3] に対応する。
  分類の考え方自体はそのまま使える。
- **ページング**: `folder_items` を `offset` を進めながら全件返す
  ジェネレータ(`yield`)にすると Ruby の Enumerator に近い使い勝手になる。
- **型ヒント**: `def folder(self, folder_id: str) -> dict:` のように付けると
  エディタ補完が効く。さらに進めるなら `dataclass` でモデル化する
  (Go / C# 実装の型定義が field 選定の参考になる)。
