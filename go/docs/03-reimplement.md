# Go: ステップバイステップ再実装ガイド

[docs/roadmap.md](../../docs/roadmap.md) の共通ステップを、
Go で具体的に進める手順。各ステップは独立して動かせる状態で終わるので、
一度にすべて実装する必要はない。

## Step 0: API を触る(実装ゼロ)

```sh
python3 mock/server.py &      # このリポジトリのルートで

curl -s -H "Authorization: Bearer x" http://localhost:8793/users/me
curl -s http://localhost:8793/users/me                    # 401 を確認
curl -s -H "Authorization: Bearer x" http://localhost:8793/folders/0/items
```

完了条件: [roadmap.md](../../docs/roadmap.md) Step 0 参照。

## Step 1: 素の HTTP GET(main 1 本)

作業ディレクトリを作り、モジュールを初期化する(Go はここが最初の一歩)。

```sh
mkdir mybox && cd mybox
go mod init mybox          # go.mod が作られる
```

`main.go`:

```go
package main

import (
	"fmt"
	"io"
	"net/http"
)

func main() {
	req, err := http.NewRequest("GET", "http://localhost:8793/users/me", nil)
	if err != nil {
		panic(err)   // 学習用の暫定。あとで消す
	}
	req.Header.Set("Authorization", "Bearer dummy-token")

	res, err := http.DefaultClient.Do(req)
	if err != nil {
		panic(err)
	}
	defer res.Body.Close()

	body, _ := io.ReadAll(res.Body)
	fmt.Println(res.StatusCode)     // => 200
	fmt.Println(string(body))       // => {"type": "user", ...}
}
```

```sh
go run .
```

試すこと:

- `req.Header.Set` の行を消すとどうなるか →
  `res.StatusCode` が 401 になるだけで、**err は nil のまま**であることを
  確認する。Go の http は非 2xx をエラー扱いしない。
  Step 3 でステータス判定を自分で書く理由がこれ。

## Step 2: クライアントの骨格(正常系のみ)

型定義とクライアントを書く。メソッドは 1 本だけ。まだ `main.go` 1 ファイルでよい。

```go
type User struct {
	Type  string `json:"type"`
	ID    string `json:"id"`
	Name  string `json:"name"`
	Login string `json:"login"`
}

type Client struct {
	baseURL     string
	accessToken string
}

func New(baseURL, accessToken string) *Client {
	return &Client{
		baseURL:     strings.TrimSuffix(baseURL, "/"),
		accessToken: accessToken,
	}
}

func (c *Client) CurrentUser() (User, error) {
	var u User
	req, err := http.NewRequest("GET", c.baseURL+"/users/me", nil)
	if err != nil {
		return u, err
	}
	req.Header.Set("Authorization", "Bearer "+c.accessToken)
	res, err := http.DefaultClient.Do(req)
	if err != nil {
		return u, err
	}
	defer res.Body.Close()
	body, err := io.ReadAll(res.Body)
	if err != nil {
		return u, err
	}
	err = json.Unmarshal(body, &u)
	return u, err
}

func main() {
	client := New("http://localhost:8793", "x")
	me, err := client.CurrentUser()
	if err != nil {
		panic(err)
	}
	fmt.Println(me.Name)
}
```

完了条件:

- ユーザー名が表示される
- `New("http://localhost:8793/", "x")`(末尾スラッシュ付き)でも動く
- トークンは Client 内部で付与されている

## Step 3: エラー 4 分類(このガイドの山場)

`errors.go` を作る:

```go
package main   // Step 7 でパッケージ分割するまでは main のままでよい

import (
	"errors"
	"fmt"
)

var ErrEmptyResponse = errors.New("response body is empty")

type HTTPError struct {
	StatusCode int
	Body       string
}

func (e *HTTPError) Error() string {
	return fmt.Sprintf("HTTP error: status=%d", e.StatusCode)
}

type ParseError struct {
	Err  error
	Body string
}

func (e *ParseError) Error() string { return fmt.Sprintf("failed to parse JSON: %v", e.Err) }
func (e *ParseError) Unwrap() error { return e.Err }

type UnexpectedResponseError struct {
	Err  error
	Body string
}

func (e *UnexpectedResponseError) Error() string { return fmt.Sprintf("unexpected response: %v", e.Err) }
func (e *UnexpectedResponseError) Unwrap() error { return e.Err }
```

共通処理をジェネリック関数 `get` に切り出し、判定を入れる。
**判定の順序(ステータス → 空 → Unmarshal)を守る**こと。

```go
func get[T any](c *Client, path string) (T, error) {
	var v T
	req, err := http.NewRequest("GET", c.baseURL+path, nil)
	if err != nil {
		return v, err
	}
	req.Header.Set("Authorization", "Bearer "+c.accessToken)
	res, err := http.DefaultClient.Do(req)
	if err != nil {
		return v, err
	}
	defer res.Body.Close()
	body, err := io.ReadAll(res.Body)
	if err != nil {
		return v, err
	}

	if res.StatusCode < 200 || res.StatusCode >= 300 {              // [1]
		return v, &HTTPError{StatusCode: res.StatusCode, Body: string(body)}
	}
	if strings.TrimSpace(string(body)) == "" {                      // [2]
		return v, ErrEmptyResponse
	}
	if err := json.Unmarshal(body, &v); err != nil {
		var typeErr *json.UnmarshalTypeError
		if errors.As(err, &typeErr) {                               // [4]
			return v, &UnexpectedResponseError{Err: err, Body: string(body)}
		}
		return v, &ParseError{Err: err, Body: string(body)}         // [3]
	}
	return v, nil
}

// CurrentUser は 1 行になる
func (c *Client) CurrentUser() (User, error) { return get[User](c, "/users/me") }
```

検収コード(main に置いて実行):

```go
paths := []string{"/broken/http-error", "/broken/empty",
	"/broken/truncated", "/broken/not-json", "/broken/scalar"}
for _, path := range paths {
	_, err := get[User](client, path)
	var httpErr *HTTPError
	var parseErr *ParseError
	var unexpectedErr *UnexpectedResponseError
	switch {
	case errors.As(err, &httpErr):
		fmt.Println(path+":", "HTTPError")
	case errors.Is(err, ErrEmptyResponse):
		fmt.Println(path+":", "ErrEmptyResponse")
	case errors.As(err, &parseErr):
		fmt.Println(path+":", "ParseError")
	case errors.As(err, &unexpectedErr):
		fmt.Println(path+":", "UnexpectedResponseError")
	default:
		fmt.Println(path+":", "分類できなかった(NG)", err)
	}
}
```

完了条件(期待する出力):

```text
/broken/http-error: HTTPError
/broken/empty: ErrEmptyResponse
/broken/truncated: ParseError
/broken/not-json: ParseError
/broken/scalar: UnexpectedResponseError
```

注意: `/broken/scalar`(Body が `42`)は、デコード先が構造体なので
UnmarshalTypeError → [4] に落ちる。ここが動的型付け言語との違い。

## Step 4: 単一リソース系エンドポイント

`Folder` / `File` の構造体を定義(02-implementation.md の models.go 参照。
**`CreatedAt *string` のポインタを忘れずに**)し、メソッドを足す。

```go
func (c *Client) User(id string) (User, error)     { return get[User](c, "/users/"+id) }
func (c *Client) Folder(id string) (Folder, error) { return get[Folder](c, "/folders/"+id) }
func (c *Client) File(id string) (File, error)     { return get[File](c, "/files/"+id) }
```

完了条件:

```go
folder, err := client.Folder("0")
fmt.Println(folder.Name)                 // => All Files
fmt.Println(folder.CreatedAt == nil)     // => true(null が nil ポインタになる)

_, err = client.File("999")
var httpErr *HTTPError
errors.As(err, &httpErr)                 // true になり、
fmt.Println(httpErr.StatusCode)          // => 404
```

## Step 5: 一覧系エンドポイント(コレクション形式)

`Collection[T]` と要素型(`Item` / `Comment` / `Collaboration`)を定義し、
メソッドを足す。

```go
type Collection[T any] struct {
	TotalCount int `json:"total_count"`
	Offset     int `json:"offset"`
	Limit      int `json:"limit"`
	Entries    []T `json:"entries"`
}

func (c *Client) FolderItems(id string) (Collection[Item], error) {
	return get[Collection[Item]](c, "/folders/"+id+"/items")
}
func (c *Client) FileComments(id string) (Collection[Comment], error) {
	return get[Collection[Comment]](c, "/files/"+id+"/comments")
}
func (c *Client) FolderCollaborations(id string) (Collection[Collaboration], error) {
	return get[Collection[Collaboration]](c, "/folders/"+id+"/collaborations")
}
```

完了条件:

```go
items, _ := client.FolderItems("0")
fmt.Println(items.TotalCount)            // => 2
for _, item := range items.Entries {
	fmt.Println(item.Type, item.Name)    // folder と file が混在して出る
}
collabs, _ := client.FolderCollaborations("0")
fmt.Println(len(collabs.Entries))        // => 0(空でも壊れない)
```

## Step 6: 検索とクエリパラメータ

`get` に `params url.Values` 引数を足し、search を追加する。

```go
func get[T any](c *Client, path string, params url.Values) (T, error) {
	...
	requestURL := c.baseURL + path
	if len(params) > 0 {
		requestURL += "?" + params.Encode()   // エスケープ込みで組み立つ
	}
	...
}

func (c *Client) Search(query string, params url.Values) (Collection[Item], error) {
	merged := url.Values{}
	for key, values := range params {
		merged[key] = values
	}
	merged.Set("query", query)
	return get[Collection[Item]](c, "/search", merged)
}
```

既存メソッドの `get` 呼び出しには第 3 引数 `nil` を足す
(コンパイラが直し漏れを全部教えてくれる。静的型付けの体験どころ)。

完了条件:

```go
results, _ := client.Search("report", nil)
results, _ = client.Search("月次 report", nil)   // 日本語・スペースもエスケープされる

_, err := client.Search("", nil)                 // モックは空 query でも通るので
_, err = get[User](client, "/search", nil)       // query なし → 400
// err が *HTTPError で StatusCode == 400 になること
```

## Step 7: 仕上げ

- パッケージを分割する: ライブラリを `package mysdkbox`
  (models.go / errors.go / client.go)、サンプルを `example/main.go`
  (`package main`)に分け、エラー型などの公開名を大文字始まりに揃える
- example に全 API 呼び出しと `errors.As/Is` 分岐の見本をまとめる
- `go vet ./...` と `gofmt -l .`(整形漏れ検出)を通す
- README を書く(このリポジトリの `go/README.md` が見本)
- (任意)`BOX_BASE_URL` を外し、実際の Box API +
  Developer Token で動かしてみる

最終形はこのリポジトリの `go/` と見比べて答え合わせできる。
