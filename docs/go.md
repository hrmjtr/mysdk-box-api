# Go 実装の解説(Ruby 経験者向け)

`go/` 以下の実装を、Ruby 実装([ruby.md](ruby.md))との対比で解説する。
API 仕様は [api.md](api.md) を先に読むこと。

Go は Ruby と考え方が大きく違う言語なので、まず前提の違いから説明する。

## Ruby との対応表

| Ruby                            | Go                                  | 備考 |
|---------------------------------|-------------------------------------|------|
| gem + `require`                 | モジュール(`go.mod`)+ `import`   | |
| `module MySdk::Box`             | `package mysdkbox`                  | 1 ディレクトリ = 1 パッケージ |
| クラス + メソッド               | 構造体 + レシーバ付き関数           | `func (c *Client) Folder(...)` |
| `initialize`                    | コンストラクタ関数 `New(...)`       | 言語機能ではなく慣習 |
| 例外(`raise` / `rescue`)      | 戻り値の `error`(多値返し)        | **最重要の違い** |
| `rescue XxxError => e`(クラス分岐)| `errors.As(err, &target)`        | |
| `rescue` で同値比較したい場合   | `errors.Is(err, ErrXxx)`            | 番兵エラー値 |
| `JSON.parse` → Hash             | `json.Unmarshal` → 構造体           | 事前に型を定義する |
| `nil` になりうる値              | ポインタ型(`*string`)             | 値型はゼロ値になり nil を表せない |
| ダックタイピング                | ジェネリクス `get[T any]`           | 本実装での使い所 |
| メソッド名 snake_case           | 公開は PascalCase                   | 小文字始まりはパッケージ内限定 |

## ファイル構成と読む順番

```text
go/
├── go.mod              # モジュール定義(gem name + Gemfile.lock に相当)
├── models.go           # 1. レスポンスの構造体定義 ← Go ではここが出発点
├── errors.go           # 2. エラー定義
├── client.go           # 3. クライアント本体
└── example/
    └── main.go         # 4. 利用例とエラーハンドリングの見本
```

Ruby では「パースした Hash をそのまま返す」で済んだが、
Go は静的型付けなので **先にレスポンスの型を定義する**。読む順番も models.go から。

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

- バッククォート内の `json:"..."` が **構造体タグ**。JSON のキー(snake_case)と
  Go のフィールド名(PascalCase)の対応を宣言する。
- JSON に含まれる未定義フィールドは黙って捨てられる(エラーにならない)。
  「必要なフィールドだけ定義する」という本リポジトリの方針と相性がよい。
- ルートフォルダの `created_at` は null になる(api.md 参照)ため
  `*string`(ポインタ)にする。値型 `string` のままだと null が空文字になり、
  「null だった」ことと「空文字だった」ことを区別できない。
- `size` はバイト数なので `int64` にしておく(大きいファイルで int32 を超える)。

### 2. コレクション型:ジェネリクスで 1 回だけ定義する

Box の一覧系は `{total_count, entries, offset, limit}` に包まれて返る(api.md 参照)。
要素の型ごとにラッパー構造体を書くと重複するので、型パラメータで共通化している。

```go
type Collection[T any] struct {
	TotalCount int `json:"total_count"`
	Offset     int `json:"offset"`
	Limit      int `json:"limit"`
	Entries    []T `json:"entries"`
}

// 使う側
func (c *Client) FileComments(id string) (Collection[Comment], error) {
	return get[Collection[Comment]](c, "/files/"+id+"/comments", nil)
}
```

Ruby 版が `["entries"]` で取り出していたものが、Go では `.Entries` になる。

### 3. エラー設計:例外がない世界(errors.go)

Go には raise/rescue がない。関数が `(結果, error)` の 2 値を返し、
呼び出し側が毎回 `if err != nil` で判定する。

エラーの「種類」は 2 通りの方法で表現している:

```go
// 方法A: 番兵エラー値 — 付随情報が不要な分類に使う
var ErrEmptyResponse = errors.New("mysdkbox: response body is empty")
// 判定: errors.Is(err, mysdkbox.ErrEmptyResponse)

// 方法B: カスタムエラー型 — 付随情報(status など)を持つ分類に使う
type HTTPError struct {
	StatusCode int
	Body       string
}
func (e *HTTPError) Error() string { ... }   // これで error インターフェースを満たす
// 判定: var httpErr *mysdkbox.HTTPError; errors.As(err, &httpErr)
```

Ruby 感覚での読み替え:

- `errors.Is` ≒ 特定のエラー**インスタンス**との比較(Ruby には近い慣習がない)
- `errors.As` ≒ `rescue HTTPError => e`(クラスで捕まえて中身を見る)
- `Unwrap()` を実装すると `errors.As/Is` がラップ元まで辿ってくれる。
  Ruby の `cause` を手動で用意するイメージ。

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

`http.Get(url)` はヘッダーを付けられないショートカットなので、
Bearer 認証には `http.NewRequest` でリクエストを組み立てて `Do` で送る。
Ruby の「`get_response(uri, headers)` に持ち替える」のと同じ話が
Go では「`Get` → `NewRequest` + `Do` に持ち替える」になる。

### 5. ジェネリクスで get を 1 つにする(client.go)

Ruby 版の private `get` は「何でも返せる」が、Go では戻り値の型を決める必要がある。
エンドポイントごとに decode 処理を書くと重複だらけになるため、
型パラメータ付きの関数 1 本に集約している。

```go
func get[T any](c *Client, path string, params url.Values) (T, error) {
	var v T          // T のゼロ値(エラー時にそのまま返す)
	...
	if err := json.Unmarshal(body, &v); err != nil { ... }
	return v, nil
}

// 呼び出し側は T を指定するだけ
func (c *Client) Folder(id string) (Folder, error) {
	return get[Folder](c, "/folders/"+id, nil)
}
```

- `T` には構造体(`Folder`)もジェネリック型(`Collection[Item]`)も入る。
- メソッドは型パラメータを持てないという Go の制約があるため、
  `get` はメソッドではなくパッケージ関数にしてある。

### 6. レスポンス判定:パースエラーと想定外の区別が Go では自然にできる

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

Ruby/Python では「JSON としては正しいが形が違う」を
`is_a?(Hash) || is_a?(Array)` で自前判定したが、Go では標準ライブラリが
エラー型で区別してくれる:

- `*json.SyntaxError` = JSON 自体が壊れている → 分類 [3]
- `*json.UnmarshalTypeError` = JSON は正しいが宣言した型に合わない → 分類 [4]

静的型付けの恩恵で、「コレクションを期待したのにスカラー値が来た」まで検出できる
(Ruby 版はスカラー値しか検出できない)。

- `http.Client.Do` は Ruby の `Net::HTTP` と同じく **非 2xx でも err を返さない**。
  err が返るのは通信自体の失敗のみ。ステータス判定は自分で書く。
- `defer res.Body.Close()` は Ruby のブロック付き open と同じ「確実に閉じる」慣用句。

### 7. 利用側のエラー分岐(example/main.go)

```go
var httpErr *mysdkbox.HTTPError
switch {
case errors.As(err, &httpErr):
	// httpErr.StatusCode, httpErr.Body が使える
case errors.Is(err, mysdkbox.ErrEmptyResponse):
	...
}
```

Ruby の `rescue` 連鎖に相当するのがこの `switch` + `errors.As/Is` パターン。

## 動かし方

```sh
python3 mock/server.py &                  # リポジトリルートで

export BOX_BASE_URL=http://localhost:8793
export BOX_ACCESS_TOKEN=dummy-token
cd go && go run ./example
```

`go run` がビルドと実行を一括で行う(bundler + ruby の関係に近いが、
依存解決・コンパイル・実行がすべて `go` コマンド 1 つで完結する)。
静的検査は `go vet ./...`、ビルドのみは `go build ./...`。

## 再実装チェックリスト

1. `go.mod` を作る(`go mod init <モジュール名>`)
2. `models.go`: api.md のデータモデルを構造体 + json タグ(snake_case)で定義。
   `Collection[T]` を用意し、null になりうるフィールドはポインタに
3. `errors.go`: 番兵 1 つ + エラー型 3 つ、`Error()` と `Unwrap()` を実装
4. `client.go`: `get[T any]` で `NewRequest` + Authorization ヘッダー、
   ステータス → 空 Body → Unmarshal の判定を実装、
   `SyntaxError` / `UnmarshalTypeError` を `errors.As` で振り分け
5. エンドポイントごとの公開メソッドを 1 行ずつ足す
6. モックサーバーの `/broken/*` 5 種で分類が正しいことを確認する

## 拡張の指針(本リポジトリではやらないこと)

- **タイムアウト**: `Client.HTTPClient` を公開フィールドにしてあるので、
  `client.HTTPClient = &http.Client{Timeout: 10 * time.Second}` と差し替えるだけ。
- **context 対応**: 実務の Go では `Folder(ctx context.Context, id string)` のように
  第一引数で ctx を受けてキャンセル可能にするのが標準的。
  `http.NewRequestWithContext` を使う形に `get` を書き換える。
- **ページング**: `FolderItems` を `offset` を進めながら全件返すヘルパーを足す。
  Go 1.23+ ならイテレータ(`iter.Seq`)で Ruby の Enumerator 風に書ける。
- **日時のパース**: `CreatedAt` を string でなく `*time.Time` にすると
  `json.Unmarshal` が ISO 8601 を自動でパースする(形式が崩れると
  UnmarshalTypeError になる点も含めて挙動を確認するとよい)。
