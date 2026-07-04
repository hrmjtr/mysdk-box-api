# Python: 実装解説

`python/` 以下の実装を、再実装できる粒度で解説する。
先に読むもの: [docs/api.md](../../docs/api.md)(API 仕様)、
[01-setup.md](01-setup.md)(環境構築と文法入門)。

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
利用側は `from mysdk_box import Client, HttpError` と
パッケージ名だけで書ける。内部のファイル分割
(client.py / errors.py)を利用者に意識させないための構成。

## 設計の要点

### 1. 依存は標準ライブラリのみ

```python
import json             # json.loads
import urllib.request   # HTTP クライアント
import urllib.parse     # クエリ文字列の組み立て
import urllib.error     # HTTPError 例外
```

実務では `requests` という定番パッケージを使うことが多いが、
「pip なしで動く」「HTTP の生の手順が見える」ことを優先して
標準の urllib を直接使う。

### 2. クライアントは「設定を持って GET するだけ」のオブジェクト

```python
class Client:
    def __init__(self, base_url, access_token):
        self.base_url = base_url.rstrip("/")   # 末尾スラッシュを正規化
        self.access_token = access_token
```

`rstrip("/")` は末尾の `/` を削る。
`https://api.box.com/2.0/` のような入力でもパス連結が壊れない。

### 3. API メソッドは短い定義を並べる

```python
def current_user(self):
    return self._get("/users/me")

def folder(self, folder_id):
    return self._get(f"/folders/{folder_id}")

def folder_items(self, folder_id, **params):
    return self._get(f"/folders/{folder_id}/items", params)

def search(self, query, **params):
    return self._get("/search", {"query": query, **params})
```

- `f"/folders/{folder_id}"` は f-string(文字列への値の埋め込み)。
- `**params` により `folder_items("0", limit=10)` のような
  キーワード引数がそのままクエリパラメータになる。
- 共通処理はすべて `_get` に寄せる(先頭 `_` は内部用の慣習)。
  **エンドポイントを増やす作業を「数行追加」にする**のがこの設計の狙い。

### 4. リクエスト:ヘッダー付きは Request オブジェクトを作る

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

1 つずつ見る:

- `urllib.parse.urlencode({"query": "a b"})` は `"query=a+b"` のように
  **エスケープ込みで**クエリ文字列を作る。文字列連結で書いてはいけない。
- `urlopen(url)` に直接ヘッダーは渡せないため、
  `urllib.request.Request` に URL とヘッダーを詰めてから `urlopen` する。
- `with ... as response:` はブロックを抜けるときに接続を確実に閉じる構文。
- `response.read()` は **bytes(バイト列)** を返す。Python は文字列(str)と
  バイト列(bytes)が別の型なので、`decode("utf-8")` で文字列にする。

**最重要ポイント: urllib は非 2xx で例外を投げる。**

多くの言語の HTTP クライアント(Ruby の Net::HTTP、Go の http、C# の
HttpClient)は 404 や 500 でも普通にレスポンスを返し、ステータス判定は
自分で書く。Python の urllib は違い、**非 2xx になると `HTTPError` 例外が
飛ぶ**。そのためこの実装では「HTTP エラーの判定」が if 文ではなく
except 節に現れる。

- 例外オブジェクト `e` 自体がレスポンスを兼ねる:
  `e.code` がステータスコード、`e.read()` が Body。
- それを自前の `HttpError` に詰め替えて raise し直す。
  利用者に urllib の例外型を意識させず、この SDK の例外体系だけで
  扱えるようにするため。
- `decode("utf-8", "replace")` は不正なバイトを置換文字にして
  デコード失敗で二次災害を起こさないための保険。
- `raise ... from e` は「元の例外 e が原因」という因果関係を残す書き方。
  スタックトレースに両方が表示され、調査しやすくなる。

### 5. レスポンス判定は `_parse` に集約

```python
def _parse(self, body):
    if not body.strip():                                   # [2] 空レスポンス
        raise EmptyResponseError("response body is empty")

    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:                      # [3] パースエラー
        raise ParseError(f"failed to parse JSON: {e}") from e

    if not isinstance(data, (dict, list)):                 # [4] 想定外
        raise UnexpectedResponseError(
            f"unexpected JSON type: {type(data).__name__}"
        )
    return data
```

- [1] HTTP エラーだけは前述の通り `_get` 側(except 節)で処理される。
  判定フローの順序自体は [api.md](../../docs/api.md) と同じ
  (ステータス → 空 → パース → 形)。
- `json.loads` はスカラー値(`"42"` という Body)も正常にパースして
  int を返してしまうので、分類 [4] の `isinstance` チェックが別途必要。
- `isinstance(data, (dict, list))` はタプル指定で「dict または list」。

### 6. エラーは 1 つの基底クラスにぶら下げる(errors.py)

```python
class BoxError(Exception):
    """すべてのエラーの基底クラス。except BoxError でまとめて捕捉できる。"""


class HttpError(BoxError):
    def __init__(self, status, body):
        super().__init__(f"HTTP error: status={status}")
        self.status = status
        self.body = body


class EmptyResponseError(BoxError): ...
class ParseError(BoxError): ...
class UnexpectedResponseError(BoxError): ...
```

- 「基底 1 つ + 4 分類」。利用側は `except BoxError` で一括捕捉も、
  個別の型で分岐もできる。分岐の見本は `example.py` にある。
- クラス直下の文字列は docstring(ドキュメント文字列)。
  `help(BoxError)` で表示される、コメントを兼ねた仕様記述。
- `super().__init__(...)` は親クラスのコンストラクタ呼び出し。
  ここでメッセージを渡しておくと `print(e)` で表示される。

### 7. 戻り値は素の dict

モデルクラスへの変換はあえてしない。

- キーは JSON のまま文字列(snake_case): `folder["item_status"]`。
- 一覧系はコレクション形式のまま返すので、要素は `["entries"]` で取り出す。
- **ないキーへのアクセスは KeyError 例外になる**(nil が返る Ruby とは違う)。
  無いかもしれないキーは `folder.get("created_at")` を使う
  (ルートフォルダの `created_at` は `None`)。

## 再実装するときの順序

[docs/roadmap.md](../../docs/roadmap.md) のステップに沿った
Python 版の具体的な手順を [03-reimplement.md](03-reimplement.md) に用意している。

## 拡張の指針(本リポジトリではやらないこと)

- **タイムアウト**: `urlopen(request, timeout=10)` の 1 引数で指定できる。
- **requests / httpx の採用**: 実務では `requests` が一般的。
  `response.raise_for_status()` が分類 [1] に、`response.json()` が投げる
  `JSONDecodeError` が [3] に対応する。4 分類の考え方はそのまま使える。
- **リトライ**: 429(レートリミット)と 5xx、通信例外
  (`urllib.error.URLError`)に限って回数制限つきで行う。
  429 は `Retry-After` ヘッダーの秒数だけ待つ。
- **ページング**: `folder_items` を `offset` を進めながら全件 `yield` する
  ジェネレータにすると、`for item in client.all_items("0"):` と書ける。
- **型ヒント**: `def folder(self, folder_id: str) -> dict:` と付けると
  エディタ補完と mypy 検査が効く。さらに進めるなら `dataclass` で
  モデル化する(Go / C# 実装の型定義がフィールド選定の参考になる)。
