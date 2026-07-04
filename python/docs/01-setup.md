# Python: 環境構築と最小限の言語入門

Python をほとんど触ったことがない人が、`python/` の実装を読み・動かし・
再実装できるようになるための最初のドキュメント。

## 環境構築

Python 3.9 以上を使う(f-string や型まわりの新しめの書き方のため。
3.12 前後を推奨)。

```sh
# バージョン確認
python3 --version

# 入っていない場合の例
# macOS:  brew install python
# Ubuntu: sudo apt install python3
```

追加のインストールは不要。この実装は標準ライブラリのみで、
pip(Python のパッケージ管理)で何かを入れる必要はない。
そのため venv(仮想環境)も作らなくてよい。

### 動作確認

```sh
# リポジトリルートで
python3 mock/server.py &                  # モック API サーバー

export BOX_BASE_URL=http://localhost:8793
export BOX_ACCESS_TOKEN=dummy-token
python3 python/example.py
```

ユーザー名やフォルダ一覧が表示されれば環境は整っている。

### 対話環境(REPL)

`python3` と打つと対話シェルが起動する。1 行ずつ試せる。

```python
$ python3
>>> 1 + 1
2
>>> "hello".upper()
'HELLO'
```

## この実装を読むのに必要な Python 文法

Python 全体ではなく、`python/` のコードに登場するものだけを説明する。

### 基本:インデントがブロック

Python には `end` や `{ }` がなく、**インデント(字下げ)がブロックを表す**。
インデントが揃っていないと文法エラーになる。

```python
# 変数(型宣言はない。すべて動的型付け)
name = "Alice"

# 文字列への埋め込み(f-string)。先頭に f を付けると {} 内が評価される
print(f"name is {name}")      # => name is Alice

# 関数定義。def 行の末尾にコロン、本体はインデント
def add(a, b):
    return a + b              # return は明示する(Ruby と違い省略できない)
```

### 辞書とリスト

```python
# 辞書(dict)。キーは文字列が基本
d = {"name": "Alice"}
d["name"]           # => 'Alice'
d["unknown"]        # KeyError 例外!(nil ではなく例外になる点に注意)
d.get("unknown")    # => None(例外にしたくないときは get を使う)

# リスト
items = [1, 2, 3]
for item in items:
    print(item)

# 内包表記(リストを変換しながら作る)。map の代わりによく使う
names = [u["name"] for u in users]
", ".join(names)    # リストを区切り文字で連結
```

### クラスと self

```python
class Client:
    # __init__ がコンストラクタ。Client(...) で呼ばれる
    # メソッドの第 1 引数は必ず self(インスタンス自身。明示的に書く)
    def __init__(self, base_url, access_token):
        self.base_url = base_url          # self.xxx がインスタンス変数
        self.access_token = access_token

    def current_user(self):
        return self._get("/users/me")     # 自分のメソッドも self. 経由で呼ぶ

    # 先頭 _ は「内部用」の目印(慣習であって、強制力はない)
    def _get(self, path):
        ...

client = Client("https://...", "xxx")     # new は書かない
client.current_user()
```

### パッケージと import

Python の名前空間はディレクトリ構造そのもの。
`mysdk_box/` ディレクトリに `__init__.py` を置くとパッケージになる。

```python
import json                        # 標準ライブラリを読み込む
from mysdk_box import Client       # パッケージから名前を取り出して読み込む
from .errors import HttpError      # 先頭の . は「同じパッケージ内から」の意味
```

`__init__.py` に `from .client import Client` と書いておくと、
利用者は `from mysdk_box import Client` と短く書ける(re-export)。

### 例外処理

```python
# 例外クラスは Exception を継承して作る
class MyError(Exception):
    pass                            # pass は「中身なし」のプレースホルダ

try:
    raise MyError("something went wrong")
except MyError as e:                # 型を指定して捕まえる
    print(e)
except (TypeError, ValueError):     # 複数の型をまとめて捕まえる
    ...

# raise X(...) from e と書くと「e が原因で X が起きた」と因果関係が残る
```

### キーワード引数と **kwargs

```python
def folder_items(self, folder_id, **params):
    # 呼び出し側が folder_items("0", limit=10) と書くと、
    # params は {"limit": 10} という辞書として受け取れる
    ...

# 辞書の展開・マージ
merged = {"query": query, **params}
```

### その他、実装に出てくるもの

```python
"abc/".rstrip("/")          # => 'abc'   末尾の指定文字を削る
not body.strip()            # 空白を削って空文字なら True(空判定の慣用句)
isinstance(data, (dict, list))  # 型判定(タプルで「いずれか」)
os.environ["KEY"]           # 環境変数。ないと KeyError
os.environ.get("KEY", "デフォルト値")
with open(...) as f:        # ブロックを抜けるとき自動でクローズされる構文
    ...
sys.exit("message")         # メッセージを stderr に出して終了コード 1 で終わる
```

## 次に読むもの

- [02-implementation.md](02-implementation.md) — 実装の設計解説
- [03-reimplement.md](03-reimplement.md) — ステップバイステップ再実装ガイド
