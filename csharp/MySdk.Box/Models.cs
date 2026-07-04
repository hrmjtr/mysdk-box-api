namespace MySdk.Box;

// レスポンスの型定義。必要最小限のフィールドのみ持つ。
// JSON のキーは camelCase だが、PropertyNameCaseInsensitive で対応付けている。

public record Space(string SpaceKey, string Name);

public record Project(int Id, string ProjectKey, string Name, bool Archived);

public record User(int Id, string UserId, string Name, string? MailAddress);

public record Status(int Id, string Name);

public record Priority(int Id, string Name);

public record Issue(
    int Id,
    string IssueKey,
    string Summary,
    string? Description,
    Status Status,
    Priority Priority,
    User? Assignee,
    User CreatedUser,
    string Created,
    string Updated);

public record Comment(int Id, string Content, User CreatedUser, string Created);
