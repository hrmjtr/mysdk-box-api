# Ruby: 環境構築と最小限の言語入門

Ruby をほとんど触ったことがない人が、`ruby/` の実装を読み・動かし・
再実装できるようになるための最初のドキュメント。

## 環境構築

Ruby 3.0 以上を使う(実装が Ruby 3.0+ の文法を使っているため)。

```sh
# バージョン確認(3.0 以上なら OK)
ruby -v

# 入っていない場合の例
# macOS:  brew install ruby
# Ubuntu: sudo apt install ruby-full
# 複数バージョンを使い分けるなら rbenv や mise を使う(このリポジトリでは不要)
```

追加のインストールは不要。この実装は標準ライブラリのみで、
gem(Ruby のパッケージ)を 1 つも入れずに動く。

### 動作確認

```sh
# リポジトリルートで
python3 mock/server.py &                  # モック API サーバー

export BOX_BASE_URL=http://localhost:8793
export BOX_ACCESS_TOKEN=dummy-token
ruby ruby/example.rb
```

ユーザー名やフォルダ一覧が表示されれば環境は整っている。

### 対話環境(irb)

`irb` と打つと対話シェルが起動する。1 行ずつ試せるので、
言語に慣れていないうちは irb で挙動を確かめながら読むとよい。

```ruby
$ irb
irb> 1 + 1
=> 2
irb> "hello".upcase
=> "HELLO"
```

## この実装を読むのに必要な Ruby 文法

Ruby 全体ではなく、`ruby/` のコードに登場するものだけを説明する。

### 基本

```ruby
# 変数(型宣言はない。すべてが動的型付け)
name = "Alice"
count = 3

# 文字列への埋め込み(式展開)。ダブルクォート内の #{} が評価される
puts "name is #{name}"       # => name is Alice

# メソッド定義。return を書かなければ最後の式の値が戻り値になる
def add(a, b)
  a + b
end

# Ruby 3.0+ の 1 行メソッド定義(endless method)。本実装で多用している
def add(a, b) = a + b
```

### ハッシュとシンボル

```ruby
# ハッシュ(他言語の dict / map)。キーには文字列もシンボルも使える
h = { "name" => "Alice" }     # 文字列キー
h = { name: "Alice" }         # シンボルキー(:name)。この書き方が一般的

# JSON.parse の戻り値は「文字列キー」のハッシュ。ここを混同しやすい
data = JSON.parse('{"name": "Alice"}')
data["name"]    # => "Alice"
data[:name]     # => nil(シンボルキーは存在しない!)

# ないキーを読んでもエラーにならず nil が返る
data["unknown"] # => nil

# ネストを nil 安全にたどる
data.dig("created_by", "name")
```

### クラスとインスタンス変数

```ruby
class Client
  # initialize がコンストラクタ。Client.new(...) で呼ばれる
  # 「base_url:」はキーワード引数(呼び出し時に名前を付けて渡す)
  def initialize(base_url:, access_token:)
    @base_url = base_url        # @ 付きがインスタンス変数(他言語の this.xxx)
    @access_token = access_token
  end

  private                        # これ以降のメソッドは外から呼べない

  def helper = "..."
end

client = Client.new(base_url: "https://...", access_token: "xxx")
```

### モジュール(名前空間)

```ruby
module MySdk
  module Box
    class Client; end
  end
end

MySdk::Box::Client.new(...)     # :: で階層をたどる
```

定数(クラス名・モジュール名)は必ず大文字で始まる。
`MySdk::box` とは書けない(小文字始まりの定数は文法エラー)。

### 例外処理

```ruby
# 例外クラスは StandardError を継承して作るのが定石
class MyError < StandardError; end

begin
  raise MyError, "something went wrong"   # 例外を投げる
rescue MyError => e                        # 型を指定して捕まえる
  puts e.message
rescue => e                                # 型なしは StandardError 全般を捕まえる
  puts "other: #{e.message}"
end
```

`rescue A => e` は「A またはそのサブクラスなら捕まえる」。
本実装がエラーを 1 つの基底クラスにぶら下げているのは、
`rescue MySdk::Box::Error` の 1 行で全部捕まえられるようにするため。

### require とファイル分割

```ruby
require "json"                  # 標準ライブラリや gem を読み込む
require_relative "box/client"   # 自分のファイルからの相対パスで読み込む
```

`ruby/lib/mysdk-box.rb` が require をまとめる「入口ファイル」で、
利用者は `require "mysdk-box"` の 1 行だけ書けばよい構成にしている。

### その他、実装に出てくるもの

```ruby
"abc/".chomp("/")      # => "abc"   末尾の指定文字を削る
"  ".strip.empty?      # => true    前後の空白を削って空か判定
res.is_a?(Hash)        # クラス判定(true / false)
ENV.fetch("KEY")       # 環境変数。ないと例外(ENV["KEY"] だと nil)
list.each { |x| ... }  # イテレーション。{ } はブロック(無名関数に近い)
list.map { |x| x * 2 } # 変換した配列を返す
warn "message"         # 標準エラー出力に表示
```

## 次に読むもの

- [02-implementation.md](02-implementation.md) — 実装の設計解説
- [03-reimplement.md](03-reimplement.md) — ステップバイステップ再実装ガイド
