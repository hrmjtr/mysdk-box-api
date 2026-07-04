# C#: 実装解説

`csharp/` 以下の実装を、再実装できる粒度で解説する。
先に読むもの: [docs/api.md](../../docs/api.md)(API 仕様)、
[01-setup.md](01-setup.md)(環境構築と文法入門)。

C# は「静的型付け + 例外あり」なので、エラー設計は Ruby / Python に近く、
型まわりは Go に近い。他の言語のドキュメントを読んだ後だと理解が早い。

## ファイル構成と読む順番

```text
csharp/
├── MySdk.Box/                  # ライブラリ本体
│   ├── MySdk.Box.csproj        #   プロジェクト定義(XML、10 行程度)
│   ├── Models.cs               # 1. レスポンスの record 定義
│   ├── Errors.cs               # 2. エラー定義
│   └── Client.cs               # 3. クライアント本体
└── Example/                    # 実行サンプル(別プロジェクト)
    ├── Example.csproj          #   MySdk.Box への ProjectReference を持つ
    └── Program.cs              # 4. 利用例とエラーハンドリングの見本
```

ライブラリと実行サンプルを別プロジェクトに分け、
`Example.csproj` の `<ProjectReference>` で参照している。
「ライブラリ」と「それを使うアプリ」を分ける .NET の標準的な構成。

## 設計の要点

### 1. モデルは record で 1 行ずつ(Models.cs)

```csharp
public record Collection<T>(int TotalCount, int Offset, int Limit, List<T> Entries);

public record User(string Type, string Id, string Name, string Login);

public record Folder(
    string Type, string Id, string Name, long Size,
    string ItemStatus, string? CreatedAt, string? ModifiedAt);
```

- record の位置引数がそのままプロパティになる(01-setup.md 参照)。
  System.Text.Json は **この位置引数コンストラクタを使って**
  デシリアライズできる(引数名と JSON キーを突き合わせる)。
- `string? CreatedAt` の `?` は null 許容注釈。
  ルートフォルダの `created_at` は null になる(api.md 参照)ので、
  そのフィールドだけ `?` を付ける。Go では「ポインタで null を表す」
  としたものが、C# では注釈 1 文字で済む。
- `Size` は `long`(64bit)。バイト数は int(32bit)の上限 2GB を超えうる。
- コレクションは Go と同じ発想でジェネリック record
  `Collection<T>` に共通化。`Collection<Comment>` のように使う。

**命名の注意 — BoxFile:**

ファイルを表す型は本来 `File` としたいが、標準ライブラリの
`System.IO.File` と名前が衝突する。ImplicitUsings 環境では
`using System.IO;` が常に有効なので、利用側コードで `File` と書くと
どちらを指すか曖昧になる。そのためこの型だけ `BoxFile` にしている。
既存の有名な型と名前が被ったときにどう折り合いを付けるかの実例。

### 2. snake_case への対応は命名ポリシー 1 行(Client.cs)

```csharp
private static readonly JsonSerializerOptions JsonOptions =
    new() { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower };
```

Box API のキーは snake_case(`total_count`)、C# のプロパティは
PascalCase(`TotalCount`)。この変換は .NET 8 で追加された
`JsonNamingPolicy.SnakeCaseLower` に一括で任せる。

- Go では json タグをフィールドごとに書いた。C# では規則が一律なら
  ポリシー 1 つで済み、例外的なキーだけ
  `[JsonPropertyName("...")]` 属性で個別指定する(本実装では不要)。
- `static readonly` にしているのは、オプションを使い回すと
  System.Text.Json が内部キャッシュを効かせられるため
  (毎回 new すると遅くなる、という定番の落とし穴)。

### 3. 例外設計(Errors.cs)

```csharp
public class BoxApiException : Exception { ... }              // 基底

public class BoxHttpException : BoxApiException              // [1] StatusCode / Body
{
    public int StatusCode { get; }
    public string Body { get; }
    ...
}
public class BoxEmptyResponseException : BoxApiException     // [2]
public class BoxParseException : BoxApiException             // [3]
public class BoxUnexpectedResponseException : BoxApiException // [4]
```

- 「基底 1 つ + 4 分類」。`catch (BoxApiException)` で一括捕捉も、
  個別の型で分岐もできる。
- C# の慣習でクラス名は `...Exception` で終える。
- `{ get; }` は読み取り専用プロパティ(値はコンストラクタで設定)。
- コンストラクタで `inner`(内部例外)を親に渡しており、
  「パース失敗の元になった JsonException」がスタックトレースに残る。

### 4. 公開メソッドは expression-bodied で 1 行(Client.cs)

```csharp
public Task<User> GetCurrentUserAsync() => GetAsync<User>("/users/me");
public Task<Folder> GetFolderAsync(string id) => GetAsync<Folder>($"/folders/{id}");
public Task<Collection<Comment>> GetFileCommentsAsync(string id)
    => GetAsync<Collection<Comment>>($"/files/{id}/comments");
```

- 全メソッドが非同期(`Task<T>` を返す)。.NET の HttpClient が
  非同期 API を基本としているため。名前の `...Async` は C# の命名慣習。
- 共通処理はジェネリックな `GetAsync<T>` に寄せ、
  **エンドポイント追加を「1 行」にする**(Go の `get[T]` と同じ狙い)。

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

- `_http.GetAsync(url)` という短い形もあるが、リクエスト単位の
  ヘッダーを付けられないので `HttpRequestMessage` + `SendAsync` を使う
  (Go の `NewRequest` + `Do` と同じ持ち替え)。
- 代替案として `HttpClient.DefaultRequestHeaders` にトークンを
  設定する方法もあるが、コンストラクタで注入された共有 HttpClient を
  書き換える副作用があるため避けた。
- `HttpClient` は **非 2xx でも例外を投げない**。
  `IsSuccessStatusCode`(2xx 判定)で自分でチェックする
  (Python の urllib だけが例外を投げる派で、Ruby / Go / C# は返す派)。
- クエリ文字列は `Uri.EscapeDataString` でキーと値を
  個別にエスケープしてから連結する(Client.cs の GetAsync 冒頭)。

### 6. パースは 2 段階:[3] と [4] を区別するため(Client.cs)

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

なぜ 2 段階に分けるのか:

System.Text.Json は「壊れた JSON」も「JSON は正しいが型に合わない」も
**同じ `JsonException`** を投げる。一発の `Deserialize<T>(body)` では
分類 [3] と [4] を区別できない。そこで:

1. `JsonDocument.Parse` で **構文だけ** 検証する。失敗 = 壊れた JSON = [3]
2. 構文が通った後の `Deserialize<T>` の失敗は「形が想定と違う」= [4]

Go は Unmarshal がエラーの型(`SyntaxError` / `UnmarshalTypeError`)で
区別してくれたが、C# では **処理を 2 段に割ることで** 同じ区別を実現する。
同じ問題への言語ごとの別解として比較すると面白い。

細部:

- `using (document)` は JsonDocument が内部バッファを借りているため
  Dispose が必要(公式ドキュメントでも必須とされている)。
- `??` は null 合体演算子。`Deserialize` は入力が JSON の `null` のとき
  null を返すので、それも [4] に倒す。

### 7. 利用側の分岐(Program.cs)

```csharp
try { ... }
catch (BoxHttpException e)              { /* e.StatusCode, e.Body */ }
catch (BoxEmptyResponseException e)     { ... }
catch (BoxParseException e)             { ... }
catch (BoxUnexpectedResponseException e){ ... }
```

catch は上から順に照合される。個別の型を先に、基底
(`BoxApiException`)でまとめたい場合は最後に書く。

## 再実装するときの順序

[docs/roadmap.md](../../docs/roadmap.md) のステップに沿った
C# 版の具体的な手順を [03-reimplement.md](03-reimplement.md) に用意している。

## 拡張の指針(本リポジトリではやらないこと)

- **タイムアウト**: コンストラクタが HttpClient を注入できるので、

  ```csharp
  new Client(url, token, new HttpClient { Timeout = TimeSpan.FromSeconds(10) })
  ```

- **HttpClient の寿命管理**: 実務ではリクエストごとに new せず
  使い回すのが定石(ソケット枯渇防止)。DI コンテナを使う環境なら
  `IHttpClientFactory` に任せる。
- **CancellationToken**: Go の context に相当。全メソッドに
  `CancellationToken cancellationToken = default` を足すと
  呼び出し側から中断できる。実務の非同期 API ではほぼ必須の作法。
- **リトライ**: 429 と 5xx、通信例外(`HttpRequestException`)に限って
  回数制限つきで行う。429 は `Retry-After` ヘッダーの秒数だけ待つ。
- **ページング**: `GetFolderItemsAsync` を `offset` を進めながら全件返す
  `IAsyncEnumerable<Item>` にすると `await foreach` で回せる。
- **日時の型**: `CreatedAt` を `DateTimeOffset?` にすると
  ISO 8601 を自動でパースする。
