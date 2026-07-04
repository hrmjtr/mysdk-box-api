package mysdkbox

// Box API のレスポンス型。必要最小限のフィールドのみ持つ。
// キーは snake_case、ID は文字列(Box API の仕様)。

// 一覧系レスポンスの共通形式
type Collection[T any] struct {
	TotalCount int `json:"total_count"`
	Offset     int `json:"offset"`
	Limit      int `json:"limit"`
	Entries    []T `json:"entries"`
}

type User struct {
	Type  string `json:"type"` // "user"
	ID    string `json:"id"`
	Name  string `json:"name"`
	Login string `json:"login"`
}

type Folder struct {
	Type       string  `json:"type"` // "folder"
	ID         string  `json:"id"`
	Name       string  `json:"name"`
	Size       int64   `json:"size"`
	ItemStatus string  `json:"item_status"`
	CreatedAt  *string `json:"created_at"` // ルートフォルダは null
	ModifiedAt *string `json:"modified_at"`
}

type File struct {
	Type       string `json:"type"` // "file"
	ID         string `json:"id"`
	Name       string `json:"name"`
	Size       int64  `json:"size"`
	SHA1       string `json:"sha1"`
	CreatedAt  string `json:"created_at"`
	ModifiedAt string `json:"modified_at"`
}

// フォルダ内アイテム・検索結果の要素。file / folder / web_link が混在する。
type Item struct {
	Type string `json:"type"`
	ID   string `json:"id"`
	Name string `json:"name"`
	Size int64  `json:"size"`
}

type Comment struct {
	Type      string `json:"type"` // "comment"
	ID        string `json:"id"`
	Message   string `json:"message"`
	CreatedBy User   `json:"created_by"`
	CreatedAt string `json:"created_at"`
}

type Collaboration struct {
	Type         string `json:"type"` // "collaboration"
	ID           string `json:"id"`
	Role         string `json:"role"` // "editor", "viewer" など
	AccessibleBy User   `json:"accessible_by"`
}
