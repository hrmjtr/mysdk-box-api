# mysdk-box (Go)

box API の読み取り系を扱う小さなクライアント。標準ライブラリのみで実装している。

## 使い方

```go
import "mysdkbox"

client := mysdkbox.New("https://example.com/api/v2", os.Getenv("BOX_API_KEY"))

space, err := client.Space()                  // スペース情報
projects, err := client.Projects()            // プロジェクト一覧
project, err := client.Project("DEMO")        // プロジェクト情報(ID またはキー)
issues, err := client.Issues(nil)             // 課題一覧
issues, err := client.Issues(url.Values{"count": {"20"}}) // クエリパラメータも渡せる
issue, err := client.Issue("DEMO-1")          // 課題情報
comments, err := client.IssueComments("DEMO-1") // 課題コメント一覧
users, err := client.Users()                  // ユーザー一覧
statuses, err := client.Statuses()            // 状態一覧
priorities, err := client.Priorities()        // 優先度一覧
```

戻り値は `models.go` に定義した構造体(必要最小限のフィールドのみ)。

## エラー

| 型 / 値                    | 意味                     | 判定方法                |
|----------------------------|--------------------------|-------------------------|
| `*HTTPError`               | 2xx 以外                 | `errors.As`             |
| `ErrEmptyResponse`         | 200 だが Body が空       | `errors.Is`             |
| `*ParseError`              | JSON として解釈できない  | `errors.As`             |
| `*UnexpectedResponseError` | JSON だが想定した形でない| `errors.As`             |

分岐の書き方は `example/main.go` の `exitIf` を参照。

## サンプルの実行

リポジトリルートでモックサーバーを起動してから実行する。

```sh
python3 ../mock/server.py &

export BOX_BASE_URL=http://localhost:8793
export BOX_API_KEY=dummy-key
go run ./example
```

## ファイル構成

```text
client.go         クライアント本体
models.go         レスポンスの構造体定義
errors.go         エラー定義
example/main.go   実行サンプル
```
