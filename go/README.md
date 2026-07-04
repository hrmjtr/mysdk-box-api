# mysdk-box (Go)

Box API の読み取り系を扱う小さなクライアント。標準ライブラリのみで実装している。

ドキュメント(Go をほとんど知らない人でも読める):

- [docs/01-setup.md](docs/01-setup.md) — 環境構築と最小限の言語入門
- [docs/02-implementation.md](docs/02-implementation.md) — 実装の設計解説
- [docs/03-reimplement.md](docs/03-reimplement.md) — ステップバイステップ再実装ガイド

## 使い方

```go
import "mysdkbox"

client := mysdkbox.New("https://api.box.com/2.0", os.Getenv("BOX_ACCESS_TOKEN"))

me, err := client.CurrentUser()                    // 現在のユーザー情報
user, err := client.User("1")                      // ユーザー情報
folder, err := client.Folder("0")                  // フォルダ情報("0" はルート)
items, err := client.FolderItems("0", nil)         // フォルダ内アイテム一覧
items, err := client.FolderItems("0", url.Values{"limit": {"10"}}) // クエリパラメータも渡せる
collabs, err := client.FolderCollaborations("11")  // コラボレーション一覧
file, err := client.File("101")                    // ファイル情報
comments, err := client.FileComments("101")        // ファイルコメント一覧
results, err := client.Search("report", nil)       // 検索
```

戻り値は `models.go` に定義した構造体(必要最小限のフィールドのみ)。
一覧系は `Collection[T]` に包まれるので、要素は `.Entries` で取り出す。

```go
for _, item := range items.Entries {
	fmt.Printf("%s: %s\n", item.Type, item.Name)
}
```

## エラー

| 型 / 値                    | 意味                     | 判定方法    |
|----------------------------|--------------------------|-------------|
| `*HTTPError`               | 2xx 以外                 | `errors.As` |
| `ErrEmptyResponse`         | 200 だが Body が空       | `errors.Is` |
| `*ParseError`              | JSON として解釈できない  | `errors.As` |
| `*UnexpectedResponseError` | JSON だが想定した形でない| `errors.As` |

分岐の書き方は `example/main.go` の `exitIf` を参照。

## サンプルの実行

リポジトリルートでモックサーバーを起動してから実行する。

```sh
python3 ../mock/server.py &

export BOX_BASE_URL=http://localhost:8793
export BOX_ACCESS_TOKEN=dummy-token
go run ./example
```

実際の Box API に対しては `BOX_BASE_URL` を外し、
`BOX_ACCESS_TOKEN` に Developer Token を設定する。

## ファイル構成

```text
client.go         クライアント本体
models.go         レスポンスの構造体定義(Collection[T] 含む)
errors.go         エラー定義
example/main.go   実行サンプル
```
