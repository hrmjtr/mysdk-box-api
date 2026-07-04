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
| キーワード引数 `params = {}`  | `**params`                    | `issues(count=20)` と書ける |
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
    def __init__(self, base_url, api_key):
        self.base_url = base_url.rstrip("/")   # Ruby の chomp("/") 相当
        self.api_key = api_key

    def projects(self):
        return self._get("/projects")

    def issues(self, **params):
        return self._get("/issues", params)
```

- Ruby の endless method のような 1 行定義はないので、通常の 2 行メソッド。
- `issues(count=20)` のようにキーワード引数がそのままクエリパラメータになる。
  Ruby 版の `issues(count: 20)` と同じ使い勝手。

### 2. リクエストと Ruby との最大の違い

```python
def _get(self, path, params=None):
    query = dict(params or {})
    query["apiKey"] = self.api_key
    url = f"{self.base_url}{path}?{urllib.parse.urlencode(query)}"

    try:
        with urllib.request.urlopen(url) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise HttpError(e.code, e.read().decode("utf-8", "replace")) from e

    return self._parse(body)
```

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

Ruby 版と同じ方針。キーは文字列。
Ruby と違って `dict["ないキー"]` は `KeyError` 例外になるため、
無いかもしれないキーは `issue.get("assignee")` を使う。

## 動かし方

```sh
python3 mock/server.py &                  # リポジトリルートで

export BOX_BASE_URL=http://localhost:8793
export BOX_API_KEY=dummy-key
python3 python/example.py
```

`example.py` と `mysdk_box/` が同じディレクトリにあるため、
そのまま import が通る(pip install は不要)。

## 再実装チェックリスト

1. `errors.py`: 基底 + 4 分類のエラークラス
2. `client.py`: `_get` で URL 組み立て(`urlencode` + `apiKey` 付与)
3. `urlopen` を try/except で囲み、`HTTPError` を自前の型に詰め替える
4. `_parse`: 空 Body → `json.loads` → `isinstance` の順で判定
5. `__init__.py` で公開名を re-export
6. モックサーバーの `/broken/*` 5 種で分類が正しいことを確認する

## 拡張の指針(本リポジトリではやらないこと)

- **タイムアウト**: `urlopen(url, timeout=10)` で指定できる(Ruby 版より簡単)。
- **requests / httpx の採用**: 実務では標準の urllib より
  `requests` が一般的。その場合 `response.raise_for_status()` が
  分類 [1] に、`response.json()` の `JSONDecodeError` が [3] に対応する。
  分類の考え方自体はそのまま使える。
- **型ヒント**: `def projects(self) -> list[dict]:` のように付けると
  エディタ補完が効く。さらに進めるなら `dataclass` でモデル化する
  (Go / C# 実装の型定義が field 選定の参考になる)。
