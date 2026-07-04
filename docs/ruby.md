# Ruby 実装の解説

`ruby/` 以下の実装を、再実装できる粒度で解説する。
API 仕様は [api.md](api.md) を先に読むこと。

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

gem の慣習(`lib/<gem名>.rb` + `lib/<名前空間ディレクトリ>/`)に合わせているが、
gemspec は用意していない。gem 化する場合は gemspec を足すだけでよい構成にしてある。

なお仕様書のサンプルは `MySdk::box::Client` だが、Ruby の定数は
大文字始まりが必須のため `MySdk::Box::Client` としている。

## 設計の要点

### 1. 依存は標準ライブラリのみ

```ruby
require "json"
require "net/http"
require "uri"
```

`faraday` や `httparty` を使えば短く書けるが、
「HTTP クライアントの生の使い方が読み取れる」ことを優先して `Net::HTTP` を直接使う。

### 2. クライアントは「設定を持って GET するだけ」のオブジェクト

```ruby
def initialize(base_url:, api_key:)
  @base_url = base_url.chomp("/")   # 末尾スラッシュを正規化
  @api_key = api_key
end
```

- キーワード引数にして呼び出し側の可読性を上げる。
- `chomp("/")` で `https://example.com/api/v2/` のような入力も受け付ける。

### 3. API メソッドは 1 行 = 1 エンドポイント

```ruby
def space                     = get("/space")
def projects                  = get("/projects")
def issues(params = {})       = get("/issues", params)
def issue_comments(id_or_key) = get("/issues/#{id_or_key}/comments")
```

Ruby 3.0+ の endless method(`def name = 式`)を使い、
「メソッド名 → パス」の対応が一覧表のように読める形にしている。
共通処理はすべて private の `get` に寄せる。

### 4. リクエストは `Net::HTTP.get_response` の単発呼び出し

```ruby
def get(path, params = {})
  uri = URI.parse(@base_url + path)
  uri.query = URI.encode_www_form(params.merge(apiKey: @api_key))
  parse_response(Net::HTTP.get_response(uri))
end
```

- `URI.encode_www_form` がエスケープを含めてクエリ文字列を組み立てる。
  文字列連結で `?apiKey=#{key}` と書かないこと(エスケープ漏れの元)。
- `params.merge(apiKey: @api_key)` で認証キーを必ず付与する。
- `Net::HTTP.get_response` は 1 リクエストごとに接続を張る最も単純な API。
  接続の使い回しが必要になったら `Net::HTTP.start` のブロック形式に置き換える
  (「拡張の指針」参照)。

### 5. レスポンス判定は `parse_response` に集約

[api.md](api.md) の判定フローをそのまま実装している。

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

- **`Net::HTTP` は非 2xx でも例外を投げず、レスポンスオブジェクトを返す。**
  ステータス判定は自分で行う必要がある。`is_a?(Net::HTTPSuccess)` が慣用句
  (`code == "200"` のような文字列比較より意図が明確で、2xx 全体を拾える)。
- `response.body` は `nil` になりうるので `to_s` で吸収する。
- `JSON.parse` はスカラー値(`42` など)も正常にパースするため、
  分類 [4] のチェック(Hash / Array か)が別途必要になる。

### 6. エラーは 1 つの基底クラスにぶら下げる

```ruby
class Error < StandardError; end          # 基底

class HttpError < Error                   # [1] status と body を保持
  attr_reader :status, :body
end
class EmptyResponseError < Error; end     # [2]
class ParseError < Error; end             # [3]
class UnexpectedResponseError < Error; end # [4]
```

- 基底を `StandardError` 継承にするのは Ruby の定石
  (`Exception` 直継承にすると裸の `rescue` で捕まらなくなる)。
- 利用側は `rescue MySdk::Box::Error` で一括、
  個別クラスで分岐、のどちらも選べる。分岐の見本は `example.rb` にある。

### 7. 戻り値は素の Hash / Array

モデルクラス(`Project` クラスなど)into 変換はあえてしない。

- 実装が短くなり、API のレスポンス構造がそのまま見える。
- キーは JSON のまま文字列(`project["projectKey"]`)。シンボルではない点に注意。
- ネストの深い取得は `issue.dig("status", "name")` を使うと nil 安全。

## 動かし方

```sh
python3 mock/server.py &                  # リポジトリルートで

export BOX_BASE_URL=http://localhost:8793
export BOX_API_KEY=dummy-key
ruby ruby/example.rb
```

`example.rb` は `$LOAD_PATH` を自分で通しているので gem install は不要。

## 再実装チェックリスト

1. エラークラス群を定義する(基底 + 4 分類)
2. `Client#initialize` で base_url 正規化と api_key 保持
3. private `get(path, params)`: URI 組み立て → `apiKey` 付与 → リクエスト
4. `parse_response`: ステータス → 空 Body → JSON.parse → 型チェック の順で判定
5. エンドポイントごとの public メソッドを 1 行ずつ足す
6. モックサーバーの `/broken/*` 5 種で分類が正しいことを確認する

## 拡張の指針(本リポジトリではやらないこと)

- **タイムアウト**: `Net::HTTP.get_response` にはタイムアウト指定がないため、
  `Net::HTTP.start(host, port, use_ssl:, open_timeout:, read_timeout:)` 形式に置き換える。
- **接続の使い回し**: 同じく `Net::HTTP.start` のブロック内で複数リクエストを送る。
- **リトライ**: 5xx と通信例外(`Errno::ECONNREFUSED`, `Net::OpenTimeout`)に限って
  回数制限つきで行う。4xx はリトライしない。
- **モデル化**: 戻り値の Hash を `Struct` や `Data`(Ruby 3.2+)に詰め替えると
  タイポが NoMethodError で検出できるようになる。型付き実装の雰囲気は
  Go / C# 実装([go.md](go.md) / [csharp.md](csharp.md))が参考になる。
