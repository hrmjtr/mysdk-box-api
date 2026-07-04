# Python: ステップバイステップ再実装ガイド

[docs/roadmap.md](../../docs/roadmap.md) の共通ステップを、
Python で具体的に進める手順。各ステップは独立して動かせる状態で終わるので、
一度にすべて実装する必要はない。

作業ディレクトリは `my-box/` のような新規ディレクトリを想定。

## Step 0: API を触る(実装ゼロ)

```sh
python3 mock/server.py &      # このリポジトリのルートで

curl -s -H "Authorization: Bearer x" http://localhost:8793/users/me
curl -s http://localhost:8793/users/me                    # 401 を確認
curl -s -H "Authorization: Bearer x" http://localhost:8793/folders/0/items
```

完了条件: [roadmap.md](../../docs/roadmap.md) Step 0 参照。

## Step 1: 素の HTTP GET(スクリプト 1 本)

`step1.py` を作る。クラスはまだ作らない。

```python
import urllib.request

request = urllib.request.Request(
    "http://localhost:8793/users/me",
    headers={"Authorization": "Bearer dummy-token"},
)
with urllib.request.urlopen(request) as response:
    print(response.status)                    # => 200
    print(response.read().decode("utf-8"))    # => {"type": "user", ...}
```

```sh
python3 step1.py
```

試すこと:

- `headers` を外すとどうなるか → **`urllib.error.HTTPError` 例外が飛ぶ**
  ことを確認する。Python の urllib は非 2xx を例外にする
  (レスポンスを返すだけの言語が多い中で、これは Python の特徴)。
  Step 3 で HTTP エラー処理が except 節になるのはこのため。

## Step 2: クライアントの骨格(正常系のみ)

`client.py` を作る。メソッドは 1 本だけ。エラー処理はまだ書かない。

```python
import json
import urllib.request


class Client:
    def __init__(self, base_url, access_token):
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token

    def current_user(self):
        return self._get("/users/me")

    def _get(self, path):
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        with urllib.request.urlopen(request) as response:
            body = response.read().decode("utf-8")
        return json.loads(body)


client = Client("http://localhost:8793", "x")
me = client.current_user()
print(me["name"])
```

完了条件:

- ユーザー名が表示される
- `Client("http://localhost:8793/", "x")`(末尾スラッシュ付き)でも動く
- トークンは Client 内部で付与されている

## Step 3: エラー 4 分類(このガイドの山場)

まず `errors.py`:

```python
class BoxError(Exception):
    """基底クラス"""


class HttpError(BoxError):
    def __init__(self, status, body):
        super().__init__(f"HTTP error: status={status}")
        self.status = status
        self.body = body


class EmptyResponseError(BoxError):
    pass


class ParseError(BoxError):
    pass


class UnexpectedResponseError(BoxError):
    pass
```

次に `_get` に HTTPError の詰め替えを入れ、判定処理 `_parse` を実装する。
**判定の順序(ステータス → 空 → パース → 形)を守る**こと。

```python
import urllib.error

def _get(self, path):
    request = urllib.request.Request(
        f"{self.base_url}{path}",
        headers={"Authorization": f"Bearer {self.access_token}"},
    )
    try:
        with urllib.request.urlopen(request) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:                    # [1]
        raise HttpError(e.code, e.read().decode("utf-8", "replace")) from e
    return self._parse(body)

def _parse(self, body):
    if not body.strip():                                   # [2]
        raise EmptyResponseError("response body is empty")
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:                      # [3]
        raise ParseError(f"failed to parse JSON: {e}") from e
    if not isinstance(data, (dict, list)):                 # [4]
        raise UnexpectedResponseError(f"unexpected JSON type: {type(data).__name__}")
    return data
```

検収スクリプト(そのまま使える):

```python
paths = ["/broken/http-error", "/broken/empty", "/broken/truncated",
         "/broken/not-json", "/broken/scalar"]
for path in paths:
    try:
        client._get(path)
        print(f"{path}: エラーにならなかった(NG)")
    except BoxError as e:
        print(f"{path}: {type(e).__name__}")
```

完了条件(期待する出力):

```text
/broken/http-error: HttpError
/broken/empty: EmptyResponseError
/broken/truncated: ParseError
/broken/not-json: ParseError
/broken/scalar: UnexpectedResponseError
```

## Step 4: 単一リソース系エンドポイント

ここからは数行ずつ足すだけ。

```python
def user(self, user_id):
    return self._get(f"/users/{user_id}")

def folder(self, folder_id):
    return self._get(f"/folders/{folder_id}")

def file(self, file_id):
    return self._get(f"/files/{file_id}")
```

完了条件:

```python
folder = client.folder("0")
print(folder["name"])              # => All Files
print(folder["created_at"])        # => None(ルートフォルダの仕様。落ちないこと)

try:
    client.file("999")
except HttpError as e:
    print(e.status)                # => 404
```

## Step 5: 一覧系エンドポイント(コレクション形式)

```python
def folder_items(self, folder_id):
    return self._get(f"/folders/{folder_id}/items")

def file_comments(self, file_id):
    return self._get(f"/files/{file_id}/comments")

def folder_collaborations(self, folder_id):
    return self._get(f"/folders/{folder_id}/collaborations")
```

Python ではコレクションを dict のまま返し、呼び出し側が `["entries"]` を使う。

完了条件:

```python
items = client.folder_items("0")
print(items["total_count"])                          # => 2
for item in items["entries"]:
    print(f"{item['type']}: {item['name']}")         # folder と file が混在して出る
print(client.folder_collaborations("0")["entries"])  # => [](空でも壊れない)
```

## Step 6: 検索とクエリパラメータ

`_get` にクエリパラメータ対応を足し、search を追加する。

```python
import urllib.parse

def folder_items(self, folder_id, **params):
    return self._get(f"/folders/{folder_id}/items", params)

def search(self, query, **params):
    return self._get("/search", {"query": query, **params})

def _get(self, path, params=None):
    url = f"{self.base_url}{path}"
    if params:
        url += f"?{urllib.parse.urlencode(params)}"
    ...
```

完了条件:

```python
for item in client.search("report")["entries"]:
    print(item["name"])
client.search("月次 report")        # 日本語・スペース入りでも壊れない(エスケープ確認)
client.folder_items("0", limit=1)

try:
    client._get("/search")           # query なし
except HttpError as e:
    print(e.status)                  # => 400
```

## Step 7: 仕上げ

- ファイルをパッケージ構成(`mysdk_box/__init__.py` + `client.py` +
  `errors.py`)に整理し、`__init__.py` で公開名を re-export する
- example スクリプトに全 API 呼び出しと except 分岐の見本をまとめる
- README を書く(このリポジトリの `python/README.md` が見本)
- (任意)`BOX_BASE_URL` を外し、実際の Box API +
  Developer Token で動かしてみる

最終形はこのリポジトリの `python/` と見比べて答え合わせできる。
