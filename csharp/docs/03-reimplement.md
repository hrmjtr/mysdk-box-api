# C#: ステップバイステップ再実装ガイド

[docs/roadmap.md](../../docs/roadmap.md) の共通ステップを、
C# で具体的に進める手順。各ステップは独立して動かせる状態で終わるので、
一度にすべて実装する必要はない。

## Step 0: API を触る(実装ゼロ)

```sh
python3 mock/server.py &      # このリポジトリのルートで

curl -s -H "Authorization: Bearer x" http://localhost:8793/users/me
curl -s http://localhost:8793/users/me                    # 401 を確認
curl -s -H "Authorization: Bearer x" http://localhost:8793/folders/0/items
```

完了条件: [roadmap.md](../../docs/roadmap.md) Step 0 参照。

## Step 1: 素の HTTP GET(コンソールアプリ 1 本)

プロジェクトを作る(C# はここが最初の一歩)。

```sh
dotnet new console -o MyBox && cd MyBox
```

`Program.cs` を全部書き換える(トップレベルステートメント):

```csharp
using System.Net.Http.Headers;

using var http = new HttpClient();
using var request = new HttpRequestMessage(
    HttpMethod.Get, "http://localhost:8793/users/me");
request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", "dummy-token");

using var response = await http.SendAsync(request);
Console.WriteLine((int)response.StatusCode);                    // => 200
Console.WriteLine(await response.Content.ReadAsStringAsync()); // => {"type": "user", ...}
```

```sh
dotnet run
```

試すこと:

- `request.Headers.Authorization` の行を消すとどうなるか →
  StatusCode が 401 になるだけで、**例外は起きない**ことを確認する。
  HttpClient は非 2xx をエラー扱いしない。
  Step 3 でステータス判定を自分で書く理由がこれ。

## Step 2: クライアントの骨格(正常系のみ)

まだ 1 プロジェクトのまま、`Client.cs` と `Models.cs` を足す。
メソッドは 1 本だけ。エラー処理はまだ書かない。

`Models.cs`:

```csharp
namespace MyBox;

public record User(string Type, string Id, string Name, string Login);
```

`Client.cs`:

```csharp
using System.Net.Http.Headers;
using System.Text.Json;

namespace MyBox;

public class Client
{
    private static readonly JsonSerializerOptions JsonOptions =
        new() { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower };

    private readonly HttpClient _http = new();
    private readonly string _baseUrl;
    private readonly string _accessToken;

    public Client(string baseUrl, string accessToken)
    {
        _baseUrl = baseUrl.TrimEnd('/');
        _accessToken = accessToken;
    }

    public async Task<User> GetCurrentUserAsync()
    {
        using var request = new HttpRequestMessage(
            HttpMethod.Get, $"{_baseUrl}/users/me");
        request.Headers.Authorization =
            new AuthenticationHeaderValue("Bearer", _accessToken);
        using var response = await _http.SendAsync(request);
        var body = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<User>(body, JsonOptions)!;
    }
}
```

`Program.cs`:

```csharp
using MyBox;

var client = new Client("http://localhost:8793", "x");
var me = await client.GetCurrentUserAsync();
Console.WriteLine(me.Name);
```

完了条件:

- ユーザー名が表示される
- `new Client("http://localhost:8793/", "x")`(末尾スラッシュ付き)でも動く
- トークンは Client 内部で付与されている

## Step 3: エラー 4 分類(このガイドの山場)

`Errors.cs`:

```csharp
namespace MyBox;

public class BoxApiException : Exception
{
    public BoxApiException(string message, Exception? inner = null)
        : base(message, inner) { }
}

public class BoxHttpException : BoxApiException
{
    public int StatusCode { get; }
    public string Body { get; }

    public BoxHttpException(int statusCode, string body)
        : base($"HTTP error: status={statusCode}")
    {
        StatusCode = statusCode;
        Body = body;
    }
}

public class BoxEmptyResponseException : BoxApiException
{
    public BoxEmptyResponseException() : base("response body is empty") { }
}

public class BoxParseException : BoxApiException
{
    public BoxParseException(string message, Exception? inner = null)
        : base($"failed to parse JSON: {message}", inner) { }
}

public class BoxUnexpectedResponseException : BoxApiException
{
    public BoxUnexpectedResponseException(string message, Exception? inner = null)
        : base($"unexpected response: {message}", inner) { }
}
```

共通処理を `GetAsync<T>` に切り出し、判定を入れる。
**判定の順序(ステータス → 空 → Parse → Deserialize)を守る**こと。
2 段階パースの理由は [02-implementation.md](02-implementation.md) の 6 節。

```csharp
private async Task<T> GetAsync<T>(string path)
{
    using var request = new HttpRequestMessage(HttpMethod.Get, $"{_baseUrl}{path}");
    request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _accessToken);
    using var response = await _http.SendAsync(request);
    var body = await response.Content.ReadAsStringAsync();

    if (!response.IsSuccessStatusCode)                              // [1]
        throw new BoxHttpException((int)response.StatusCode, body);
    if (string.IsNullOrWhiteSpace(body))                            // [2]
        throw new BoxEmptyResponseException();

    JsonDocument document;
    try
    {
        document = JsonDocument.Parse(body);                        // 段階1
    }
    catch (JsonException e)
    {
        throw new BoxParseException(e.Message, e);                  // [3]
    }

    using (document)
    {
        try
        {
            var value = document.Deserialize<T>(JsonOptions);       // 段階2
            return value ?? throw new BoxUnexpectedResponseException("response is JSON null");
        }
        catch (JsonException e)
        {
            throw new BoxUnexpectedResponseException(e.Message, e); // [4]
        }
    }
}

// GetCurrentUserAsync は 1 行になる
public Task<User> GetCurrentUserAsync() => GetAsync<User>("/users/me");
```

検収コード(Program.cs に置いて実行):

```csharp
var paths = new[] { "/broken/http-error", "/broken/empty",
    "/broken/truncated", "/broken/not-json", "/broken/scalar" };
foreach (var path in paths)
{
    try
    {
        await client.GetCurrentUserAsync_ForPath(path);  // 検証用に path を受ける
        Console.WriteLine($"{path}: エラーにならなかった(NG)");
    }
    catch (BoxApiException e)
    {
        Console.WriteLine($"{path}: {e.GetType().Name}");
    }
}
```

(検証のために `GetAsync<User>(path)` を呼べる internal メソッドを
一時的に生やすか、`GetAsync` を一時的に public にするとよい)

完了条件(期待する出力):

```text
/broken/http-error: BoxHttpException
/broken/empty: BoxEmptyResponseException
/broken/truncated: BoxParseException
/broken/not-json: BoxParseException
/broken/scalar: BoxUnexpectedResponseException
```

注意: `/broken/scalar`(Body が `42`)は構文としては正しい JSON なので
段階 1 を通過し、`User` への変換で失敗して [4] に落ちる。

## Step 4: 単一リソース系エンドポイント

`Folder` / `BoxFile` の record を定義(02-implementation.md 参照。
**`string? CreatedAt` の null 許容と、`File` ではなく `BoxFile` にする
名前衝突対策を忘れずに**)し、メソッドを足す。

```csharp
public Task<User> GetUserAsync(string id) => GetAsync<User>($"/users/{id}");
public Task<Folder> GetFolderAsync(string id) => GetAsync<Folder>($"/folders/{id}");
public Task<BoxFile> GetFileAsync(string id) => GetAsync<BoxFile>($"/files/{id}");
```

完了条件:

```csharp
var folder = await client.GetFolderAsync("0");
Console.WriteLine(folder.Name);                  // => All Files
Console.WriteLine(folder.CreatedAt is null);     // => True(null を安全に扱える)

try { await client.GetFileAsync("999"); }
catch (BoxHttpException e) { Console.WriteLine(e.StatusCode); }   // => 404
```

## Step 5: 一覧系エンドポイント(コレクション形式)

`Collection<T>` と要素の record(`Item` / `Comment` / `Collaboration`)を
定義し、メソッドを足す。

```csharp
public record Collection<T>(int TotalCount, int Offset, int Limit, List<T> Entries);
public record Item(string Type, string Id, string Name, long Size);

public Task<Collection<Item>> GetFolderItemsAsync(string id)
    => GetAsync<Collection<Item>>($"/folders/{id}/items");
public Task<Collection<Comment>> GetFileCommentsAsync(string id)
    => GetAsync<Collection<Comment>>($"/files/{id}/comments");
public Task<Collection<Collaboration>> GetFolderCollaborationsAsync(string id)
    => GetAsync<Collection<Collaboration>>($"/folders/{id}/collaborations");
```

完了条件:

```csharp
var items = await client.GetFolderItemsAsync("0");
Console.WriteLine(items.TotalCount);             // => 2
foreach (var item in items.Entries)
    Console.WriteLine($"{item.Type}: {item.Name}");  // folder と file が混在して出る

var collabs = await client.GetFolderCollaborationsAsync("0");
Console.WriteLine(collabs.Entries.Count);        // => 0(空でも壊れない)
```

## Step 6: 検索とクエリパラメータ

`GetAsync<T>` にクエリ辞書の引数を足し、search を追加する。
エスケープは `Uri.EscapeDataString` で行う。

```csharp
private async Task<T> GetAsync<T>(string path, IReadOnlyDictionary<string, string>? query = null)
{
    var url = $"{_baseUrl}{path}";
    if (query is { Count: > 0 })
    {
        var parameters = query.Select(kv =>
            $"{Uri.EscapeDataString(kv.Key)}={Uri.EscapeDataString(kv.Value)}");
        url += $"?{string.Join("&", parameters)}";
    }
    ...
}

public Task<Collection<Item>> SearchAsync(string query)
    => GetAsync<Collection<Item>>("/search",
        new Dictionary<string, string> { ["query"] = query });
```

完了条件:

```csharp
foreach (var item in (await client.SearchAsync("report")).Entries)
    Console.WriteLine(item.Name);
await client.SearchAsync("月次 report");   // 日本語・スペースもエスケープされる

// query なしの /search → 400 が BoxHttpException で捕捉できること
```

## Step 7: 仕上げ

- プロジェクトを分割する:

  ```sh
  dotnet new classlib -o MySdk.Box     # ライブラリ
  dotnet new console -o Example        # サンプル
  dotnet add Example reference MySdk.Box
  ```

  Client / Models / Errors をライブラリ側へ、利用コードを Example へ移す
- Example に全 API 呼び出しと catch 分岐の見本をまとめる
- `dotnet build` が警告 0 で通ることを確認する
  (null 許容の警告が出たら型設計を見直すサイン)
- README を書く(このリポジトリの `csharp/README.md` が見本)
- (任意)`BOX_BASE_URL` を外し、実際の Box API +
  Developer Token で動かしてみる

最終形はこのリポジトリの `csharp/` と見比べて答え合わせできる。
