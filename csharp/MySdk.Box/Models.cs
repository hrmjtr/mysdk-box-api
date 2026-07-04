namespace MySdk.Box;

// Box API のレスポンス型。必要最小限のフィールドのみ持つ。
// JSON のキーは snake_case、ID は文字列(Box API の仕様)。
// キーの対応付けは JsonNamingPolicy.SnakeCaseLower で行う(Client.cs 参照)。

/// <summary>一覧系レスポンスの共通形式</summary>
public record Collection<T>(int TotalCount, int Offset, int Limit, List<T> Entries);

public record User(string Type, string Id, string Name, string Login);

/// <summary>CreatedAt はルートフォルダで null になる</summary>
public record Folder(
    string Type,
    string Id,
    string Name,
    long Size,
    string ItemStatus,
    string? CreatedAt,
    string? ModifiedAt);

// System.IO.File と名前が衝突するため、この型だけ Box 接頭辞を付けている
// (ImplicitUsings 環境では using System.IO が常に有効なため)。
public record BoxFile(
    string Type,
    string Id,
    string Name,
    long Size,
    string Sha1,
    string CreatedAt,
    string ModifiedAt);

/// <summary>フォルダ内アイテム・検索結果の要素。file / folder / web_link が混在する。</summary>
public record Item(string Type, string Id, string Name, long Size);

public record Comment(string Type, string Id, string Message, User CreatedBy, string CreatedAt);

public record Collaboration(string Type, string Id, string Role, User AccessibleBy);
