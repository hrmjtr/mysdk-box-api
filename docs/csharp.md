# C# 実装の解説(Ruby 経験者向け)

`csharp/` 以下の実装を、Ruby 実装([ruby.md](ruby.md))との対比で解説する。
API 仕様は [api.md](api.md) を先に読むこと。

C# は「静的型付け + 例外あり」なので、エラー設計は Ruby に近く、
型まわりは Go に近い。両方のドキュメントを読んだ後だと理解が早い。

## Ruby との対応表

| Ruby                          | C#                                   | 備考 |
|-------------------------------|--------------------------------------|------|
| gem / gemspec                 | プロジェクト(`.csproj`)            | XML で依存とターゲットを宣言 |
| `require`                     | `using`(名前空間の取り込み)        | ファイル単位の読み込みは不要 |
| `module MySdk::Box`           | `namespace MySdk.Box`                | |
| `initialize`                  | コンストラクタ(クラス名と同名)     | |
| `StandardError` 継承          | `Exception` 継承                     | 例外設計はほぼ同じ感覚 |
| `rescue XxxError => e`        | `catch (XxxException e)`             | |
| `attr_reader :status`         | `public int StatusCode { get; }`     | 読み取り専用プロパティ |
| `Struct` / `Data`(Ruby 3.2)| `record`                             | 値ベースの等価性も同じ |
| `nil` 許容                    | `string?` / `User?`(null 許容注釈)| コンパイラが null チェックを警告 |
| `JSON.parse` → Hash           | `JsonSerializer` → 型付きオブジェクト| Go と同じく事前に型定義 |
| メソッド定義は snake_case     | 公開メソッドは PascalCase            | 非同期は `...Async` 接尾辞 |
| (対応なし)                  | `async` / `await`, `Task<T>`         | **最重要の違い** |

## ファイル構成と読む順番

```text
csharp/
├── MySdk.Box/                  # ライブラリ本体(gem に相当)
│   ├── MySdk.Box.csproj        #   プロジェクト定義
│   ├── Models.cs               # 1. レスポンスの record 定義
│   ├── Errors.cs               # 2. エラー定義
│   └── Client.cs               # 3. クライアント本体
└── Example/                    # 実行サンプル(別プロジェクト)
    ├── Example.csproj          #   MySdk.Box への ProjectReference を持つ
    └── Program.cs              # 4. 利用例とエラーハンドリングの見本
```

C# は「ソリューション > プロジェクト」の単位で管理する。
ここではライブラリと実行サンプルを別プロジェクトに分け、
`Example.csproj` の `<ProjectReference>` で参照している
(gem を Gemfile の `path:` 指定で読み込むのに近い)。

## 設計の要点

### 1. モデルは record で 1 行ずつ(Models.cs)

```csharp
public record Collection<T>(int TotalCount, int Offset, int Limit, List<T> Entries);
public record Folder(
    string Type, string Id, string Name, long Size,
    string ItemStatus, string? CreatedAt, string? ModifiedAt);
public record BoxFile(
    string Type, string Id, string Name, long Size,
    string Sha1, string CreatedAt, string ModifiedAt);
```

- `record` は Ruby 3.2 の `Data.define` に近い:イミュータブルで、
  値ベースの `==` と読みやすい `ToString()` が自動生成される。
- この「位置引数コンストラクタ」形式のまま JSON デシリアライズできる
  (System.Text.Json がコンストラクタ引数名とキーを突き合わせる)。
- `string?` は **null 許容注釈**。api.md で null になりうると定義した
  フィールド(ルートフォルダの `created_at` など)にだけ `?` を付ける。
  Go の「ポインタで null を表す」と目的は同じで、書き味はこちらが楽。
- コレクションは Go と同じ発想でジェネリック record `Collection<T>` に共通化。
- **命名の注意**: ファイルを表す型は本来 `File` としたいが、
  `System.IO.File` と衝突する(ImplicitUsings 環境では `using System.IO` が
  常に有効)ため、この型だけ `BoxFile` にしている。
  実利用で名前衝突にどう折り合いを付けるかの実例として参照。

### 2. snake_case への対応は命名ポリシー 1 行(Client.cs)

```csharp
private static readonly JsonSerializerOptions JsonOptions =
    new() { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower };
```

Box API のキーは snake_case(`total_count`)、C# のプロパティは
PascalCase(`TotalCount`)。この変換は .NET 8 の
`JsonNamingPolicy.SnakeCaseLower` に任せる。
Go では json タグをフィールドごとに書いたが、C# では規則が一律なら
ポリシー 1 つで済む(個別対応が必要なときだけ `[JsonPropertyName("...")]` を使う)。

### 3. 例外設計は Ruby とほぼ同じ(Errors.cs)

```csharp
public class BoxApiException : Exception { ... }              // 基底

public class BoxHttpException : BoxApiException              // [1] StatusCode / Body
public class BoxEmptyResponseException : BoxApiException     // [2]
public class BoxParseException : BoxApiException             // [3]
public class BoxUnexpectedResponseException : BoxApiException // [4]
```

「基底 1 つ + 4 分類」で Ruby 版と同型。`catch (BoxApiException)` で一括捕捉できる。
C# の慣習として、クラス名は `...Exception` で終える。
`inner`(内部例外)にパース時の元例外を渡しており、これは Ruby の `cause` に相当する。

### 4. async/await:Ruby にない最大の要素(Client.cs)

```csharp
public Task<Folder> GetFolderAsync(string id) => GetAsync<Folder>($"/folders/{id}");
```

- `HttpClient` の API は非同期が基本なので、クライアントも全メソッドを
  非同期(`Task<T>` を返す)にしてある。メソッド名の `...Async` は C# の命名慣習。
- 利用側は `await client.GetFolderAsync("0")` と書く。`await` した時点で
  結果(`Folder`)が取り出され、例外もここで throw される。
  **感覚としては Ruby の同期呼び出しと同じように読んでよい。**
  スレッドをブロックせずに待つ、という実行モデルだけが違う。
- `=>` はメソッド本体が式 1 つのときの短縮形(expression-bodied member)。
  Ruby の endless method(`def folder(id) = get(...)`)と同じ用途。

### 5. リクエスト:Bearer ヘッダーはリクエストごとに付ける(Client.cs)

```csharp
using var request = new HttpRequestMessage(HttpMethod.Get, url);
request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _accessToken);

using var response = await _http.SendAsync(request);
var body = await response.Content.ReadAsStringAsync();

if (!response.IsSuccessStatusCode)
    throw new BoxHttpException((int)response.StatusCode, body);   // [1]
if (string.IsNullOrWhiteSpace(body))
    throw new BoxEmptyResponseException();                        // [2]
```

- `_http.GetAsync(url)` にはヘッダーを渡せないので、
  `HttpRequestMessage` を組み立てて `SendAsync` で送る
  (Go の `NewRequest` + `Do` と同じ持ち替え)。
  `HttpClient.DefaultRequestHeaders` に設定する方法もあるが、
  注入された共有 `HttpClient` を書き換える副作用があるため避けた。
- `HttpClient` は Ruby の `Net::HTTP` と同じく **非 2xx でも例外を投げない**。
  `IsSuccessStatusCode`(2xx 判定)で自分でチェックする。
- `using var` はスコープを抜けるときに Dispose する構文
  (Ruby のブロック付き open 相当)。
- `string.IsNullOrWhiteSpace` = Ruby の `body.strip.empty?` + nil チェック。

パース部分は **2 段階** に分けている。ここがこの実装の工夫点:

```csharp
JsonDocument document;
try
{
    document = JsonDocument.Parse(body);        // 段階1: JSON として正しいか
}
catch (JsonException e)
{
    throw new BoxParseException(e.Message, e);                    // [3]
}

using (document)
{
    try
    {
        var value = document.Deserialize<T>(JsonOptions);         // 段階2: 型に合うか
        return value ?? throw new BoxUnexpectedResponseException("response is JSON null");
    }
    catch (JsonException e)
    {
        throw new BoxUnexpectedResponseException(e.Message, e);   // [4]
    }
}
```

なぜ 2 段階か: System.Text.Json は「壊れた JSON」も「型に合わない JSON」も
同じ `JsonException` を投げるため、一発の `Deserialize<T>` では
分類 [3] と [4] を区別できない。
そこで先に `JsonDocument.Parse` で構文だけ検証し(失敗 = [3])、
その後の型変換の失敗を [4] とみなす。
Go では例外の型(`SyntaxError` / `UnmarshalTypeError`)で区別できたものを、
C# では **処理を 2 段に割ることで** 区別している。同じ問題への別解として比較すると面白い。

`??` は null 合体演算子(Ruby の `||` の null 限定版)。
`Deserialize` は入力が JSON の `null` のとき null を返すので、これも [4] に倒す。

### 6. 利用側の分岐(Program.cs)

```csharp
try { ... }
catch (BoxHttpException e)              { /* e.StatusCode, e.Body */ }
catch (BoxEmptyResponseException e)     { ... }
catch (BoxParseException e)             { ... }
catch (BoxUnexpectedResponseException e){ ... }
```

Ruby の rescue 連鎖と同じ形。`Program.cs` はトップレベルステートメント
(クラスや Main を書かないスクリプト風の書き方)で、`await` も直接書ける。

## 動かし方

```sh
python3 mock/server.py &                  # リポジトリルートで

export BOX_BASE_URL=http://localhost:8793
export BOX_ACCESS_TOKEN=dummy-token
cd csharp && dotnet run --project Example
```

`dotnet run` が依存解決 → ビルド → 実行まで行う。ビルドのみは
`dotnet build Example`。.NET 8 SDK が必要。

## 再実装チェックリスト

1. `dotnet new classlib` でライブラリ、`dotnet new console` でサンプルを作り、
   `dotnet add Example reference MySdk.Box` で参照を張る
2. `Models.cs`: api.md のデータモデルを record で定義
   (`Collection<T>` を用意、null 許容に `?`、`File` の名前衝突に注意)
3. `Errors.cs`: 基底 + 4 分類の Exception
4. `Client.cs`: `SnakeCaseLower` の JsonOptions、`HttpRequestMessage` +
   Bearer ヘッダー、ステータス → 空 Body → Parse → Deserialize の判定
   (2 段階パースで [3] と [4] を区別)
5. エンドポイントごとの公開メソッドを expression-bodied で 1 行ずつ足す
6. モックサーバーの `/broken/*` 5 種で分類が正しいことを確認する

## 拡張の指針(本リポジトリではやらないこと)

- **タイムアウト**: コンストラクタが `HttpClient` を注入できるので、
  `new Client(url, token, new HttpClient { Timeout = TimeSpan.FromSeconds(10) })`。
- **HttpClient の寿命管理**: 実務ではリクエストごとに new せず
  使い回すのが定石(ソケット枯渇防止)。DI コンテナがあるなら
  `IHttpClientFactory` を使う。
- **CancellationToken**: Go の context に相当。全メソッドに
  `CancellationToken cancellationToken = default` を足すと呼び出し側から中断できる。
- **ページング**: `GetFolderItemsAsync` を `offset` を進めながら全件返す
  `IAsyncEnumerable<Item>`(`await foreach` で回せる)にすると
  Ruby の Enumerator に近い使い勝手になる。
- **日時の型**: `CreatedAt` を `DateTimeOffset?` にすると ISO 8601 を自動パースする。
