# mysdk-box (C#)

Box API の読み取り系を扱う小さなクライアント。.NET 8 の標準ライブラリ
(`HttpClient`, `System.Text.Json`)のみで実装している。

実装の設計解説と再実装の手引き(Ruby 経験者向け)は
[docs/csharp.md](../docs/csharp.md) にある。

## 使い方

```csharp
using MySdk.Box;

var client = new Client(
    baseUrl: "https://api.box.com/2.0",
    accessToken: Environment.GetEnvironmentVariable("BOX_ACCESS_TOKEN")!);

await client.GetCurrentUserAsync();                 // 現在のユーザー情報
await client.GetUserAsync("1");                     // ユーザー情報
await client.GetFolderAsync("0");                   // フォルダ情報("0" はルート)
await client.GetFolderItemsAsync("0");              // フォルダ内アイテム一覧
await client.GetFolderItemsAsync("0",               // クエリパラメータも渡せる
    new Dictionary<string, string> { ["limit"] = "10" });
await client.GetFolderCollaborationsAsync("11");    // コラボレーション一覧
await client.GetFileAsync("101");                   // ファイル情報
await client.GetFileCommentsAsync("101");           // ファイルコメント一覧
await client.SearchAsync("report");                 // 検索
```

戻り値は `Models.cs` に定義した record(必要最小限のフィールドのみ)。
一覧系は `Collection<T>` に包まれるので、要素は `.Entries` で取り出す。
ファイルを表す型は `System.IO.File` との衝突を避けるため `BoxFile`
という名前になっている(詳細は docs/csharp.md)。

```csharp
foreach (var item in (await client.GetFolderItemsAsync("0")).Entries)
    Console.WriteLine($"{item.Type}: {item.Name}");
```

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
export BOX_ACCESS_TOKEN=dummy-token
dotnet run --project Example
```

実際の Box API に対しては `BOX_BASE_URL` を外し、
`BOX_ACCESS_TOKEN` に Developer Token を設定する。

## ファイル構成

```text
MySdk.Box/Client.cs    クライアント本体
MySdk.Box/Models.cs    レスポンスの record 定義(Collection<T> 含む)
MySdk.Box/Errors.cs    エラー定義
Example/Program.cs     実行サンプル
```
