# Go: 実装解説

`go/` 以下の実装を、再実装できる粒度で解説する。
先に読むもの: [docs/api.md](../../docs/api.md)(API 仕様)、
[01-setup.md](01-setup.md)(環境構築と文法入門)。

## ファイル構成と読む順番

```text
go/
├── go.mod              # モジュール定義(module mysdkbox)
├── models.go           # 1. レスポンスの構造体定義 ← Go ではここが出発点
├── errors.go           # 2. エラー定義
├── client.go           # 3. クライアント本体
└── example/
    └── main.go         # 4. 利用例とエラーハンドリングの見本
```

動的型付け言語なら「パースした dict をそのまま返す」で済むが、
Go は静的型付けなので **先にレスポンスの型を定義する**。
読む順番も models.go から。

`example/` は `package main`(実行可能プログラム)で、
同じモジュール内のライブラリ `mysdkbox` を import して使う。
「ライブラリ」と「それを使う実行ファイル」を分ける Go の標準的な構成。

## 設計の要点

### 1. モデル定義と JSON タグ(models.go)

```go
type Folder struct {
	Type       string  `json:"type"`
	ID         string  `json:"id"`          // Box の ID は文字列
	Name       string  `json:"name"`
	Size       int64   `json:"size"`
	ItemStatus string  `json:"item_status"`
	CreatedAt  *string `json:"created_at"`  // ルートフォルダは null → ポインタ
	ModifiedAt *string `json:"modified_at"`
}
```

- `json:"item_status"` の部分が構造体タグ。JSON のキー(snake_case)と
  Go のフィールド名(PascalCase)の対応を宣言する。
  タグを書かないと Unmarshal は「フィールド名の大文字小文字ゆるめ一致」で
  探すが、snake_case とは一致しないので必須。
- JSON に含まれる未定義フィールドは黙って捨てられる(エラーにならない)。
  「必要なフィールドだけ定義する」という本リポジトリの方針と相性がよい。
- ルートフォルダの `created_at` は null になる(api.md 参照)ため
  `*string`(ポインタ)にする。値型 `string` のままだと null が
  空文字 `""` になってしまい、「null だった」と「空文字だった」を
  区別できない。
- `Size` は `int64`。バイト数は 2GB(int32 の上限)を超えうる。

### 2. コレクション型:ジェネリクスで 1 回だけ定義する

Box の一覧系は `{total_count, entries, offset, limit}` に包まれて返る。
要素の型ごとにラッパー構造体を書くと同じ定義を何度も書くことになるので、
型パラメータで共通化する。

```go
type Collection[T any] struct {
	TotalCount int `json:"total_count"`
	Offset     int `json:"offset"`
	Limit      int `json:"limit"`
	Entries    []T `json:"entries"`
}
```

`Collection[Comment]` と書けば「Comment の一覧」、
`Collection[Item]` なら「Item の一覧」になる。
利用側は `.Entries` で要素のスライスを取り出す。

### 3. エラー設計:例外がない世界(errors.go)

Go の関数は `(結果, error)` を返し、呼び出し側が `if err != nil` で
判定する(01-setup.md 参照)。「エラーの種類」は 2 通りの方法で表現する。

```go
// 方法A: 番兵エラー値 — 付随情報が不要な分類に使う
var ErrEmptyResponse = errors.New("mysdkbox: response body is empty")
// 判定: errors.Is(err, mysdkbox.ErrEmptyResponse)

// 方法B: カスタムエラー型 — 付随情報(status など)を持つ分類に使う
type HTTPError struct {
	StatusCode int
	Body       string
}

// Error() string を実装した型は error として扱える(インターフェース)
func (e *HTTPError) Error() string {
	return fmt.Sprintf("mysdkbox: HTTP error: status=%d", e.StatusCode)
}
// 判定: var httpErr *mysdkbox.HTTPError
//       errors.As(err, &httpErr)  → 一致すれば httpErr に代入され true
```

- `errors.Is(err, 値)` は「err はこのエラー値(またはそれをラップしたもの)か」。
- `errors.As(err, &型変数)` は「err はこの型(またはそれをラップしたものか)。
  そうなら取り出す」。例外のある言語の「型で catch する」に相当する。
- `ParseError` / `UnexpectedResponseError` には `Unwrap() error` も
  実装してあり、`errors.Is/As` が内側の元エラーまで辿れるようにしている
  (エラーの因果関係を保持する Go の慣習)。

4 分類との対応: [1] `*HTTPError` / [2] `ErrEmptyResponse` /
[3] `*ParseError` / [4] `*UnexpectedResponseError`。

### 4. リクエスト:ヘッダー付きは NewRequest + Do(client.go)

```go
req, err := http.NewRequest(http.MethodGet, requestURL, nil)
if err != nil {
	return v, err
}
req.Header.Set("Authorization", "Bearer "+c.accessToken)

res, err := c.HTTPClient.Do(req)
```

`http.Get(url)` という 1 行のショートカットもあるが、ヘッダーを
付けられない。Bearer 認証が必要なので、リクエストオブジェクトを
組み立てて(`NewRequest`)送信する(`Do`)形を使う。

`Client` 構造体の `HTTPClient *http.Client` は公開フィールドにしてあり、
利用者がタイムアウト付きのものに差し替えられる(拡張の指針参照)。

### 5. ジェネリクスで get を 1 つにする(client.go)

エンドポイントごとに「GET して判定してデコード」を書くと重複だらけに
なる。違いは「どの型にデコードするか」だけなので、型パラメータ付きの
関数 1 本に集約する。

```go
func get[T any](c *Client, path string, params url.Values) (T, error) {
	var v T          // T のゼロ値。エラー時はこれをそのまま返す
	...
	if err := json.Unmarshal(body, &v); err != nil { ... }
	return v, nil
}

// 公開メソッドは 1 行になる
func (c *Client) Folder(id string) (Folder, error) {
	return get[Folder](c, "/folders/"+id, nil)
}
func (c *Client) FileComments(id string) (Collection[Comment], error) {
	return get[Collection[Comment]](c, "/files/"+id+"/comments", nil)
}
```

- `T` には構造体(`Folder`)もジェネリック型(`Collection[Item]`)も入る。
- Go の制約で **メソッドは型パラメータを持てない** ため、
  `get` はメソッドではなくパッケージ内関数(小文字始まり = 非公開)に
  してある。
- **エンドポイント追加を「1 行」にする**のがこの設計の狙い。

### 6. レスポンス判定:[3] と [4] の区別が Go では自然にできる

```go
if res.StatusCode < 200 || res.StatusCode >= 300 {
	return v, &HTTPError{StatusCode: res.StatusCode, Body: string(body)}  // [1]
}
if strings.TrimSpace(string(body)) == "" {
	return v, ErrEmptyResponse                                            // [2]
}
if err := json.Unmarshal(body, &v); err != nil {
	var typeErr *json.UnmarshalTypeError
	if errors.As(err, &typeErr) {
		return v, &UnexpectedResponseError{Err: err, Body: string(body)}  // [4]
	}
	return v, &ParseError{Err: err, Body: string(body)}                   // [3]
}
```

動的型付け言語(Ruby / Python)では「JSON としては正しいが形が違う」を
「パース結果がオブジェクトでも配列でもない」という自前チェックで
判定した。Go では標準ライブラリの Unmarshal がエラーの型で
区別してくれる:

- `*json.SyntaxError` = JSON 自体が壊れている → 分類 [3]
- `*json.UnmarshalTypeError` = JSON は正しいが宣言した型に合わない → 分類 [4]

静的型付けの恩恵で「コレクションを期待したのにスカラー値が来た」まで
検出できる(動的型付け実装ではスカラー値しか検出できない)。

その他:

- `http.Client.Do` は **非 2xx でも err を返さない**。err が返るのは
  通信自体の失敗(接続不可・タイムアウト)のみ。ステータス判定は自分で書く。
- `defer res.Body.Close()` で Body の確実なクローズを予約している。

### 7. 利用側のエラー分岐(example/main.go)

```go
var httpErr *mysdkbox.HTTPError
var parseErr *mysdkbox.ParseError
switch {
case errors.As(err, &httpErr):
	fmt.Fprintf(os.Stderr, "HTTP error: status=%d body=%s\n",
		httpErr.StatusCode, httpErr.Body)
case errors.Is(err, mysdkbox.ErrEmptyResponse):
	fmt.Fprintln(os.Stderr, "empty response")
case errors.As(err, &parseErr):
	...
}
```

`switch { case 条件: }` は if-else if の連鎖の Go らしい書き方。
例外のある言語の catch 連鎖に相当するのがこのパターン。

## 再実装するときの順序

[docs/roadmap.md](../../docs/roadmap.md) のステップに沿った
Go 版の具体的な手順を [03-reimplement.md](03-reimplement.md) に用意している。

## 拡張の指針(本リポジトリではやらないこと)

- **タイムアウト**: `HTTPClient` が公開フィールドなので差し替えるだけ。

  ```go
  client.HTTPClient = &http.Client{Timeout: 10 * time.Second}
  ```

- **context 対応**: 実務の Go では第一引数で `context.Context` を受けて
  キャンセル・タイムアウトを呼び出し側から制御できるようにするのが標準的。
  `http.NewRequestWithContext(ctx, ...)` を使う形に `get` を書き換える。
- **リトライ**: 429 と 5xx、通信エラーに限って回数制限つきで行う。
  429 は `Retry-After` ヘッダーの秒数だけ待つ。
- **ページング**: `FolderItems` を `offset` を進めながら全件返すヘルパーを
  足す。Go 1.23+ ならイテレータ(`iter.Seq`)で `for item := range ...` と
  書ける。
- **日時のパース**: `CreatedAt` を `*time.Time` にすると Unmarshal が
  ISO 8601 を自動でパースする(形式が崩れると UnmarshalTypeError に
  なる = 分類 [4] に落ちる、という挙動も確認するとよい)。
