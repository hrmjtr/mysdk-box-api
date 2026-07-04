# Go: 環境構築と最小限の言語入門

Go をほとんど触ったことがない人が、`go/` の実装を読み・動かし・
再実装できるようになるための最初のドキュメント。

## 環境構築

Go 1.22 以上を使う(ジェネリクスなど新しめの機能を使うため)。

```sh
# バージョン確認
go version

# 入っていない場合
# macOS:  brew install go
# Ubuntu: sudo apt install golang-go(古い場合あり)
# 公式:   https://go.dev/dl/ からダウンロードして展開が確実
```

追加のインストールは不要。この実装は標準ライブラリのみ。

### 動作確認

```sh
# リポジトリルートで
python3 mock/server.py &                  # モック API サーバー

export BOX_BASE_URL=http://localhost:8793
export BOX_ACCESS_TOKEN=dummy-token
cd go && go run ./example
```

ユーザー名やフォルダ一覧が表示されれば環境は整っている。

### go コマンドの基本

Go には REPL がない。代わりに `go run` で書いてすぐ実行できる。

```sh
go run ./example      # ビルドして実行(使い捨て)
go build ./...        # 全パッケージをビルド(コンパイルエラーの確認)
go vet ./...          # 静的検査(怪しいコードの検出)
gofmt -w .            # コード整形(Go ではフォーマットが完全に統一されている)
```

`./...` は「このディレクトリ以下すべて」の意味。

## この実装を読むのに必要な Go 文法

Go は Ruby / Python のような動的言語とは考え方が大きく違う。
`go/` のコードに登場するものだけを説明する。

### 静的型付けとコンパイル

すべての変数・引数・戻り値に型がある。型が合わないとコンパイルが通らない。
実行前に多くの間違いが機械的に見つかる、というのが Go の体験の中心。

```go
var name string = "Alice"   // 明示的な型宣言
name := "Alice"             // := は宣言 + 型推論(関数の中でだけ使える)
count := 3                  // int と推論される
```

### パッケージと公開・非公開

1 ディレクトリ = 1 パッケージ。ファイル先頭の `package 名` で宣言する。

```go
package mysdkbox

// 大文字始まり = パッケージ外に公開される(public)
func New(...) *Client { ... }
type Client struct { ... }

// 小文字始まり = パッケージ内限定(private)
func get(...) { ... }
```

**識別子の大文字・小文字が可視性を決める**。キーワードは存在しない。

モジュール(依存管理の単位)は `go.mod` で定義する。
このリポジトリでは `module mysdkbox` の 1 行 + Go バージョンだけ。

### 構造体とメソッド

Go にはクラスがない。データは構造体(struct)、振る舞いは
「レシーバ付き関数」として別々に定義する。

```go
// データ
type Client struct {
	baseURL     string
	accessToken string
}

// 振る舞い。(c *Client) がレシーバで、「Client のメソッド」になる
// c は他言語の this / self に相当(名前は自由)
func (c *Client) CurrentUser() (User, error) {
	...
}

// コンストラクタは言語機能ではなく、New という名前の関数を書く慣習
func New(baseURL, accessToken string) *Client {
	return &Client{baseURL: baseURL, accessToken: accessToken}
}
```

`*Client` の `*` はポインタ(後述)。メソッドのレシーバは
ポインタにするのが通例と思ってよい。

### エラー処理:例外がない

**Go には例外(raise / rescue)がない。** 失敗しうる関数は
`(結果, error)` の 2 つの値を返し、呼び出し側が毎回チェックする。

```go
folder, err := client.Folder("0")
if err != nil {
	// エラー処理。nil は「値がない」(他言語の null)
	return err
}
fmt.Println(folder.Name)
```

この `if err != nil` の連続が Go のコードの見た目の特徴。
冗長に見えるが、「どこで失敗しうるか」がすべて明示されるという設計思想。

エラーの種類を判定する道具が 2 つある(実装解説で詳述):

```go
errors.Is(err, ErrEmptyResponse)   // 特定のエラー値と比較
var httpErr *HTTPError
errors.As(err, &httpErr)           // 特定のエラー型なら取り出す
```

### ポインタと nil

```go
var s string    // 値型。ゼロ値は ""(nil にできない)
var p *string   // ポインタ型。ゼロ値は nil(「値がない」を表せる)
if p != nil {
	fmt.Println(*p)   // * を付けて中身を取り出す(デリファレンス)
}
```

本実装では「JSON で null になりうるフィールド」をポインタ型にしている。
値型のままだと null と空文字を区別できないため。

### 構造体タグと JSON

```go
type User struct {
	ID   string `json:"id"`     // バッククォート内が「タグ」
	Name string `json:"name"`   // JSON のキーとの対応を宣言する
}

var u User
err := json.Unmarshal(body, &u)   // JSON バイト列 → 構造体
```

`&u` の `&` は「u のアドレスを渡す」。Unmarshal は渡された先に
書き込むため、ポインタで渡す必要がある。

### defer

```go
res, err := http.Get(url)
if err != nil { return err }
defer res.Body.Close()   // この関数を抜けるときに必ず実行される
```

後始末の予約。Python の with、Ruby のブロック付き open に相当する。

### ジェネリクス(型パラメータ)

```go
// T は呼び出し時に決まる型。any は「任意の型」の制約
func get[T any](c *Client, path string) (T, error) {
	var v T   // T のゼロ値
	...
}

user, err := get[User](c, "/users/me")        // T = User
items, err := get[[]Item](c, "/folders/0/items")  // T = Item のスライス
```

本実装では「JSON をどの型にデコードするか」だけが違う共通処理を
1 つの関数にまとめるために使っている。

### その他、実装に出てくるもの

```go
strings.TrimSuffix(s, "/")     // 末尾の "/" を削る
strings.TrimSpace(s)           // 前後の空白を削る
fmt.Printf("%s: %d\n", s, n)   // 書式付き出力(%v は「いい感じに表示」)
fmt.Fprintf(os.Stderr, ...)    // 標準エラー出力へ
os.Getenv("KEY")               // 環境変数(ないと空文字)
url.Values{}                   // クエリパラメータの入れ物(map の一種)
for _, item := range items { } // イテレーション。_ は「使わない値」の捨て場
```

## 次に読むもの

- [02-implementation.md](02-implementation.md) — 実装の設計解説
- [03-reimplement.md](03-reimplement.md) — ステップバイステップ再実装ガイド
