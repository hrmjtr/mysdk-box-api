# Ruby: 実装解説

`ruby/` 以下の実装を、再実装できる粒度で解説する。
先に読むもの: [docs/api.md](../../docs/api.md)(API 仕様)、
[01-setup.md](01-setup.md)(環境構築と文法入門)。

## ファイル構成と読む順番

```text
ruby/
├── lib/
│   ├── mysdk-box.rb            # 1. エントリポイント(require をまとめるだけ)
│   └── mysdk/box/
│       ├── errors.rb           # 2. エラー定義(約 30 行)
│       └── client.rb           # 3. クライアント本体(約 60 行)
└── example.rb                  # 4. 利用例とエラーハンドリングの見本
```

この配置は Ruby の gem(パッケージ)の標準的な慣習
「`lib/<gem名>.rb` を入口にして、実体は `lib/<名前空間のディレクトリ>/` に置く」
に合わせている。gemspec(パッケージ定義ファイル)は用意していないが、
gem 化する場合はそれを足すだけでよい構成にしてある。

## 設計の要点

### 1. 依存は標準ライブラリのみ

```ruby
require "json"       # JSON.parse
require "net/http"   # HTTP クライアント
require "uri"        # URL の組み立て・エスケープ
```

`faraday` や `httparty` といった人気の HTTP gem を使えば短く書けるが、
「HTTP クライアントの生の使い方が読み取れる」ことを優先して
標準の `Net::HTTP` を直接使う。依存ゼロなので `bundle install` も不要。

### 2. クライアントは「設定を持って GET するだけ」のオブジェクト

```ruby
class Client
  def initialize(base_url:, access_token:)
    @base_url = base_url.chomp("/")   # 末尾スラッシュを正規化
    @access_token = access_token
  end
end
```

- `base_url:` のようにキーワード引数にしているのは、呼び出し側で
  `Client.new(base_url: ..., access_token: ...)` と引数の意味が読めるようにするため。
- `chomp("/")` は末尾に `/` があれば削る。`https://api.box.com/2.0/` のような
  入力でもパス連結が `//users/me` にならない。

### 3. API メソッドは 1 行 = 1 エンドポイント

```ruby
def current_user                  = get("/users/me")
def user(id)                      = get("/users/#{id}")
def folder(id)                    = get("/folders/#{id}")
def folder_items(id, params = {}) = get("/folders/#{id}/items", params)
def search(query, params = {})    = get("/search", params.merge(query: query))
```

- `def name = 式` は Ruby 3.0+ の 1 行メソッド定義。
  「メソッド名 → パス」の対応が一覧表のように読める。
- `params = {}` はデフォルト引数。`folder_items("0")` とも
  `folder_items("0", limit: 10)` とも呼べる
  (`limit: 10` はハッシュ `{limit: 10}` として渡る)。
- 共通処理はすべて private の `get` に寄せる。
  **エンドポイントを増やす作業を「1 行追加」にする**のがこの設計の狙い。

### 4. リクエスト:Bearer 認証はヘッダーで渡す

```ruby
def get(path, params = {})
  uri = URI.parse(@base_url + path)
  uri.query = URI.encode_www_form(params) unless params.empty?
  headers = { "Authorization" => "Bearer #{@access_token}" }
  parse_response(Net::HTTP.get_response(uri, headers))
end
```

1 行ずつ見る:

- `URI.parse` は URL 文字列を URI オブジェクトに変換する。
- `URI.encode_www_form({query: "a b"})` は `"query=a+b"` のように
  **エスケープ込みで**クエリ文字列を作る。
  文字列連結で `"?query=#{q}"` と書いてはいけない(スペースや日本語で壊れる)。
- `unless params.empty?` は「params が空でなければ」(if の否定形)。
- `Net::HTTP.get_response(uri, headers)` は GET を 1 回送って
  レスポンスオブジェクトを返す、最も単純な API。
  第 2 引数でヘッダーを渡せるのは **Ruby 3.0 以降**。
  それ以前や細かい制御(タイムアウト等)が必要な場合は
  `Net::HTTP::Get.new(uri)` + `Net::HTTP.start` の形にする(後述の拡張の指針)。

### 5. レスポンス判定は `parse_response` に集約

[api.md](../../docs/api.md) の判定フロー(ステータス → 空 → パース → 形)を
そのまま実装している。

```ruby
def parse_response(response)
  body = response.body.to_s

  unless response.is_a?(Net::HTTPSuccess)                       # [1] HTTP エラー
    raise HttpError.new(status: response.code.to_i, body: body)
  end
  raise EmptyResponseError, "response body is empty" if body.strip.empty?  # [2]

  begin
    data = JSON.parse(body)
  rescue JSON::ParserError => e
    raise ParseError, "failed to parse JSON: #{e.message}"      # [3]
  end

  unless data.is_a?(Hash) || data.is_a?(Array)                  # [4]
    raise UnexpectedResponseError, "unexpected JSON type: #{data.class}"
  end
  data
end
```

Ruby 固有の注意点:

- **`Net::HTTP` は 404 や 500 でも例外を投げない。** 正常にレスポンス
  オブジェクトが返ってくるので、ステータス判定は自分で行う。
  `response.is_a?(Net::HTTPSuccess)` が慣用句で、2xx 系のレスポンスクラス
  すべてに true になる(`code == "200"` のような文字列比較より安全)。
- `response.body` は `nil` になりうるので `to_s` で空文字に変換して吸収する。
- `response.code` は文字列(`"404"`)なので `to_i` で数値にする。
- `JSON.parse` はスカラー値(`"42"` という Body など)も正常にパースして
  Integer を返してしまう。だから分類 [4] のチェック
  (Hash か Array か)が別途必要になる。

### 6. エラーは 1 つの基底クラスにぶら下げる(errors.rb)

```ruby
module MySdk
  module Box
    class Error < StandardError; end          # 基底

    class HttpError < Error                   # [1]
      attr_reader :status, :body              # 読み取り用アクセサを自動定義

      def initialize(status:, body:)
        @status = status
        @body = body
        super("HTTP error: status=#{status}") # 親クラスにメッセージを渡す
      end
    end

    class EmptyResponseError < Error; end     # [2]
    class ParseError < Error; end             # [3]
    class UnexpectedResponseError < Error; end # [4]
  end
end
```

- 基底を `StandardError` 継承にするのは Ruby の定石。
  `Exception` を直接継承すると、型指定なしの `rescue` で捕まらなくなり、
  利用者を驚かせる。
- `attr_reader :status, :body` は `def status; @status; end` を
  自動生成するマクロ。エラーオブジェクトから `e.status` で参照できる。
- 利用側は `rescue MySdk::Box::Error` で 4 分類まとめて捕捉することも、
  個別クラスで分岐することもできる。分岐の見本は `example.rb` にある。

### 7. 戻り値は素の Hash

モデルクラス(`Folder` クラスなど)への変換はあえてしない。

- 実装が短くなり、API のレスポンス構造がそのまま見える。
- キーは JSON のまま **文字列**(`folder["item_status"]`)。
  シンボル(`folder[:item_status]`)では取れない点に注意。
- 一覧系は Box のコレクション形式のまま返すので、
  要素は `["entries"]` で取り出す。
- ネストの深い取得は `comment.dig("created_by", "name")` を使うと、
  途中が nil でも例外にならない。

## 再実装するときの順序

[docs/roadmap.md](../../docs/roadmap.md) のステップに沿った
Ruby 版の具体的な手順を [03-reimplement.md](03-reimplement.md) に用意している。

## 拡張の指針(本リポジトリではやらないこと)

- **タイムアウト**: `Net::HTTP.get_response` には指定手段がないため、
  次の形に置き換える。

  ```ruby
  Net::HTTP.start(uri.host, uri.port,
                  use_ssl: uri.scheme == "https",
                  open_timeout: 5, read_timeout: 10) do |http|
    request = Net::HTTP::Get.new(uri)
    request["Authorization"] = "Bearer #{@access_token}"
    http.request(request)
  end
  ```

- **接続の使い回し**: 上記 `Net::HTTP.start` のブロック内で複数リクエストを
  送れば TCP 接続を再利用できる。
- **リトライ**: 429(レートリミット)と 5xx、通信例外
  (`Errno::ECONNREFUSED`, `Net::OpenTimeout`)に限って回数制限つきで行う。
  429 は `Retry-After` ヘッダーの秒数だけ待つ。他の 4xx はリトライしない。
- **ページング**: `folder_items` を `offset` を進めながら全件たどる
  `each_item` のような Enumerator にすると便利。
- **モデル化**: Hash を `Data.define`(Ruby 3.2+)に詰め替えると
  タイポが NoMethodError で検出できる。型付きの雰囲気は
  Go / C# 実装(`go/docs/` / `csharp/docs/`)が参考になる。
