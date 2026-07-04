# C#: 環境構築と最小限の言語入門

C# をほとんど触ったことがない人が、`csharp/` の実装を読み・動かし・
再実装できるようになるための最初のドキュメント。

## 環境構築

.NET 8 SDK 以上を使う(C# 12 の文法と
`JsonNamingPolicy.SnakeCaseLower` のため)。

```sh
# バージョン確認(8.0.x 以上なら OK)
dotnet --version

# 入っていない場合
# macOS:  brew install dotnet-sdk
# Ubuntu: https://learn.microsoft.com/dotnet/core/install/linux
# 公式:   https://dotnet.microsoft.com/download
```

追加のパッケージは不要。この実装は .NET 標準ライブラリのみ。

### 動作確認

```sh
# リポジトリルートで
python3 mock/server.py &                  # モック API サーバー

export BOX_BASE_URL=http://localhost:8793
export BOX_ACCESS_TOKEN=dummy-token
cd csharp && dotnet run --project Example
```

ユーザー名やフォルダ一覧が表示されれば環境は整っている
(初回はビルドが走るので数十秒かかる)。

### dotnet コマンドの基本

```sh
dotnet new console -o MyApp   # コンソールアプリの雛形を作る
dotnet new classlib -o MyLib  # ライブラリの雛形を作る
dotnet run --project MyApp    # ビルドして実行
dotnet build MyApp            # ビルドのみ(コンパイルエラーの確認)
```

C# のコードは「プロジェクト」(`.csproj` ファイルがあるディレクトリ)
単位で管理される。`.csproj` は XML で、対象フレームワークや
プロジェクト間の参照を宣言する(このリポジトリの csproj は 10 行程度)。

## この実装を読むのに必要な C# 文法

C# 全体ではなく、`csharp/` のコードに登場するものだけを説明する。

### 基本:静的型付け + クラスベース

```csharp
// 変数。var は型推論(型がないのではなく、コンパイラが決める)
string name = "Alice";
var count = 3;                  // int と推論される

// 文字列への埋め込み。先頭に $ を付けると {} 内が評価される
Console.WriteLine($"name is {name}");

// メソッド。戻り値の型を先に書く
int Add(int a, int b)
{
    return a + b;
}

// 本体が式 1 つなら => で短く書ける(expression-bodied)
int Add(int a, int b) => a + b;
```

### 名前空間と using

```csharp
namespace MySdk.Box;            // このファイルの型の所属(ファイル先頭に 1 行)

using System.Text.Json;         // 他の名前空間の型を短い名前で使う宣言
```

このリポジトリの csproj には `<ImplicitUsings>enable</ImplicitUsings>` が
あり、`System` / `System.IO` / `System.Net.Http` など頻出の using は
書かなくても有効になっている。

### クラスとコンストラクタ

```csharp
public class Client
{
    // フィールド。readonly はコンストラクタ以降変更不可、_ 接頭辞は慣習
    private readonly string _baseUrl;

    // コンストラクタ(クラス名と同名)。string? の ? は「null かもしれない」
    public Client(string baseUrl, HttpClient? http = null)
    {
        _baseUrl = baseUrl.TrimEnd('/');
        // ?? は「左が null なら右」(null 合体演算子)
        _http = http ?? new HttpClient();
    }
}

var client = new Client("https://...");
```

`public` / `private` が公開範囲。`string?` のような null 許容注釈は
コンパイラが「null チェック漏れ」を警告してくれる仕組みで、
`?` のない参照型は「null にならない」宣言になる。

### record(この実装のデータ型はすべてこれ)

```csharp
public record User(string Type, string Id, string Name, string Login);
```

この 1 行で「4 つの読み取り専用プロパティを持つイミュータブルな型」が
できる。値ベースの等価比較(`==`)と読みやすい `ToString()` も
自動生成される。JSON のデシリアライズ先としてそのまま使える。

### 例外処理

```csharp
public class MyException : Exception
{
    public MyException(string message) : base(message) { }   // 親に転送
}

try
{
    throw new MyException("something went wrong");
}
catch (MyException e)          // 型を指定して捕まえる
{
    Console.WriteLine(e.Message);
}
```

例外設計は Ruby / Python とほぼ同じ感覚で読める。

### async / await(この実装の最重要トピック)

.NET の HTTP クライアントは非同期 API が基本。
非同期メソッドは結果を直接ではなく `Task<T>`(未来の結果)で返す。

```csharp
// 定義側: async を付け、Task<T> を返す。名前は ...Async が慣習
public async Task<string> FetchAsync()
{
    var response = await _http.GetAsync(url);   // await で完了を待つ
    return await response.Content.ReadAsStringAsync();
}

// 利用側
var body = await client.FetchAsync();
```

**読むときは「await = その場で結果が出る同期呼び出し」とみなしてよい。**
例外も await した場所で throw される。同期と違うのは
「待っている間スレッドをブロックしない」という実行モデルだけで、
このリポジトリを読む上でそれを意識する場面はない。

### using(2 つの意味に注意)

```csharp
using System.Text.Json;         // ① ファイル先頭: 名前空間の取り込み

using var response = await ...; // ② 文の先頭: スコープを抜けるとき
                                //    自動で Dispose(後始末)する
```

②は Python の with に相当する。

### トップレベルステートメント(Program.cs)

`Example/Program.cs` にはクラスも Main メソッドもなく、
いきなり文が書いてある。これはトップレベルステートメントという
省略記法で、コンパイラが Main を補ってくれる。`await` も直接書ける。

### その他、実装に出てくるもの

```csharp
s.TrimEnd('/')                          // 末尾の '/' を削る
string.IsNullOrWhiteSpace(s)            // null または空白のみなら true
string.Join(", ", items)                // 連結
items.Select(u => u.Name)               // LINQ。map に相当(u => ... はラムダ式)
foreach (var item in items) { }         // イテレーション
Environment.GetEnvironmentVariable("KEY")  // 環境変数(ないと null)
Console.Error.WriteLine(...)            // 標準エラー出力
new Dictionary<string, string> { ["limit"] = "10" }  // 辞書リテラル
```

## 次に読むもの

- [02-implementation.md](02-implementation.md) — 実装の設計解説
- [03-reimplement.md](03-reimplement.md) — ステップバイステップ再実装ガイド
