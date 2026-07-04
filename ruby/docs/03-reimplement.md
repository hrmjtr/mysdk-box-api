# Ruby: ステップバイステップ再実装ガイド

[docs/roadmap.md](../../docs/roadmap.md) の共通ステップを、
Ruby で具体的に進める手順。各ステップは独立して動かせる状態で終わるので、
一度にすべて実装する必要はない。

作業ディレクトリは `my-box/` のような新規ディレクトリを想定
(このリポジトリの `ruby/` を写経してもよいが、
自分でゼロから書くほうが身につく)。

## Step 0: API を触る(実装ゼロ)

```sh
python3 mock/server.py &      # このリポジトリのルートで

curl -s -H "Authorization: Bearer x" http://localhost:8793/users/me
curl -s http://localhost:8793/users/me                    # 401 を確認
curl -s -H "Authorization: Bearer x" http://localhost:8793/folders/0/items
```

完了条件: [roadmap.md](../../docs/roadmap.md) Step 0 参照。

## Step 1: 素の HTTP GET(スクリプト 1 本)

`step1.rb` を作る。クラスはまだ作らない。

```ruby
require "net/http"
require "uri"

uri = URI.parse("http://localhost:8793/users/me")
headers = { "Authorization" => "Bearer dummy-token" }
response = Net::HTTP.get_response(uri, headers)

puts response.code    # => 200
puts response.body    # => {"type": "user", ...}
```

```sh
ruby step1.rb
```

試すこと:

- `headers` を渡さないとどうなるか → `response.code` が `401` になり、
  **例外は起きない**ことを確認する(Ruby の Net::HTTP の重要な性質。
  Step 3 でステータス判定を自分で書く理由がこれ)。

## Step 2: クライアントの骨格(正常系のみ)

`client.rb` を作る。メソッドは 1 本だけ。エラー処理はまだ書かない。

```ruby
require "json"
require "net/http"
require "uri"

class Client
  def initialize(base_url:, access_token:)
    @base_url = base_url.chomp("/")
    @access_token = access_token
  end

  def current_user = get("/users/me")

  private

  def get(path)
    uri = URI.parse(@base_url + path)
    headers = { "Authorization" => "Bearer #{@access_token}" }
    response = Net::HTTP.get_response(uri, headers)
    JSON.parse(response.body)
  end
end

client = Client.new(base_url: "http://localhost:8793", access_token: "x")
me = client.current_user
puts me["name"]
```

完了条件:

- ユーザー名が表示される
- `base_url: "http://localhost:8793/"`(末尾スラッシュ付き)でも動く
- トークンは Client 内部で付与されている

## Step 3: エラー 4 分類(このガイドの山場)

まず `errors.rb`:

```ruby
class Error < StandardError; end

class HttpError < Error
  attr_reader :status, :body
  def initialize(status:, body:)
    @status = status
    @body = body
    super("HTTP error: status=#{status}")
  end
end

class EmptyResponseError < Error; end
class ParseError < Error; end
class UnexpectedResponseError < Error; end
```

次に `get` を分割し、判定処理を `parse_response` として実装する。
**判定の順序(ステータス → 空 → パース → 形)を守る**こと。

```ruby
def get(path)
  uri = URI.parse(@base_url + path)
  headers = { "Authorization" => "Bearer #{@access_token}" }
  parse_response(Net::HTTP.get_response(uri, headers))
end

def parse_response(response)
  body = response.body.to_s
  unless response.is_a?(Net::HTTPSuccess)
    raise HttpError.new(status: response.code.to_i, body: body)
  end
  raise EmptyResponseError, "response body is empty" if body.strip.empty?
  begin
    data = JSON.parse(body)
  rescue JSON::ParserError => e
    raise ParseError, "failed to parse JSON: #{e.message}"
  end
  unless data.is_a?(Hash) || data.is_a?(Array)
    raise UnexpectedResponseError, "unexpected JSON type: #{data.class}"
  end
  data
end
```

検収スクリプト(そのまま使える):

```ruby
paths = %w[/broken/http-error /broken/empty /broken/truncated /broken/not-json /broken/scalar]
paths.each do |path|
  client.send(:get, path)          # send は private メソッドを呼ぶ検証用の裏口
  puts "#{path}: エラーにならなかった(NG)"
rescue Error => e
  puts "#{path}: #{e.class}"
end
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

ここからは 1 行ずつ足すだけ。基盤ができていることを実感できるはず。

```ruby
def user(id)   = get("/users/#{id}")
def folder(id) = get("/folders/#{id}")
def file(id)   = get("/files/#{id}")
```

完了条件:

```ruby
folder = client.folder("0")
puts folder["name"]              # => All Files
p folder["created_at"]           # => nil(ルートフォルダの仕様。落ちないこと)

begin
  client.file("999")
rescue HttpError => e
  puts e.status                  # => 404
end
```

## Step 5: 一覧系エンドポイント(コレクション形式)

```ruby
def folder_items(id)          = get("/folders/#{id}/items")
def file_comments(id)         = get("/files/#{id}/comments")
def folder_collaborations(id) = get("/folders/#{id}/collaborations")
```

Ruby ではコレクションを Hash のまま返し、呼び出し側が `["entries"]` を使う。

完了条件:

```ruby
items = client.folder_items("0")
puts items["total_count"]                            # => 2
items["entries"].each { |i| puts "#{i["type"]}: #{i["name"]}" }
                                                     # folder と file が混在して出る
p client.folder_collaborations("0")["entries"]       # => [](空でも壊れない)
```

## Step 6: 検索とクエリパラメータ

`get` にクエリパラメータ対応を足し、search を追加する。

```ruby
def folder_items(id, params = {}) = get("/folders/#{id}/items", params)
def search(query, params = {})    = get("/search", params.merge(query: query))

private

def get(path, params = {})
  uri = URI.parse(@base_url + path)
  uri.query = URI.encode_www_form(params) unless params.empty?
  ...
end
```

完了条件:

```ruby
client.search("report")["entries"].each { |i| puts i["name"] }
client.search("月次 report")     # 日本語・スペース入りでも壊れない(エスケープ確認)
client.folder_items("0", limit: 1)

begin
  client.send(:get, "/search")   # query なし
rescue HttpError => e
  puts e.status                  # => 400
end
```

## Step 7: 仕上げ

- ファイルを gem 慣習の配置(`lib/mysdk-box.rb` + `lib/mysdk/box/*.rb`)に
  整理し、モジュール `MySdk::Box` で名前空間を切る
- example スクリプトに全 API 呼び出しと rescue 分岐の見本をまとめる
- README を書く(このリポジトリの `ruby/README.md` が見本)
- (任意)`BOX_BASE_URL` を外し、実際の Box API +
  Developer Token で動かしてみる

最終形はこのリポジトリの `ruby/` と見比べて答え合わせできる。
