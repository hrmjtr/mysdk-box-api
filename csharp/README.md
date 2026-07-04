# mysdk-box (C#)

box API の読み取り系を扱う小さなクライアント。.NET 8 の標準ライブラリ
(`HttpClient`, `System.Text.Json`)のみで実装している。

実装の設計解説と再実装の手引き(Ruby 経験者向け)は
[docs/csharp.md](../docs/csharp.md) にある。

## 使い方

```csharp
using MySdk.Box;

var client = new Client(
    baseUrl: "https://example.com/api/v2",
    apiKey: Environment.GetEnvironmentVariable("BOX_API_KEY")!);

await client.GetSpaceAsync();                  // スペース情報
await client.GetProjectsAsync();               // プロジェクト一覧
await client.GetProjectAsync("DEMO");          // プロジェクト情報(ID またはキー)
await client.GetIssuesAsync();                 // 課題一覧
await client.GetIssuesAsync(new Dictionary<string, string> { ["count"] = "20" }); // クエリパラメータも渡せる
await client.GetIssueAsync("DEMO-1");          // 課題情報
await client.GetIssueCommentsAsync("DEMO-1");  // 課題コメント一覧
await client.GetUsersAsync();                  // ユーザー一覧
await client.GetStatusesAsync();               // 状態一覧
await client.GetPrioritiesAsync();             // 優先度一覧
```

戻り値は `Models.cs` に定義した record(必要最小限のフィールドのみ)。

## エラー

すべて `BoxApiException` を継承している。

| クラス                           | 意味                              |
|----------------------------------|-----------------------------------|
| `BoxHttpException`               | 2xx 以外(`StatusCode` `Body` 参照)|
| `BoxEmptyResponseException`      | 200 だが Body が空                |
| `BoxParseException`              | JSON として解釈できない           |
| `BoxUnexpectedResponseException` | JSON だが想定した形でない         |

## サンプルの実行

リポジトリルートでモックサーバーを起動してから実行する。

```sh
python3 ../mock/server.py &

export BOX_BASE_URL=http://localhost:8793
export BOX_API_KEY=dummy-key
dotnet run --project Example
```

## ファイル構成

```text
MySdk.Box/Client.cs    クライアント本体
MySdk.Box/Models.cs    レスポンスの record 定義
MySdk.Box/Errors.cs    エラー定義
Example/Program.cs     実行サンプル
```
