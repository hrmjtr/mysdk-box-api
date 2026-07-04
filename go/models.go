package mysdkbox

type Space struct {
	SpaceKey string `json:"spaceKey"`
	Name     string `json:"name"`
}

type Project struct {
	ID         int    `json:"id"`
	ProjectKey string `json:"projectKey"`
	Name       string `json:"name"`
	Archived   bool   `json:"archived"`
}

type User struct {
	ID          int    `json:"id"`
	UserID      string `json:"userId"`
	Name        string `json:"name"`
	MailAddress string `json:"mailAddress"`
}

type Status struct {
	ID   int    `json:"id"`
	Name string `json:"name"`
}

type Priority struct {
	ID   int    `json:"id"`
	Name string `json:"name"`
}

type Issue struct {
	ID          int      `json:"id"`
	IssueKey    string   `json:"issueKey"`
	Summary     string   `json:"summary"`
	Description string   `json:"description"`
	Status      Status   `json:"status"`
	Priority    Priority `json:"priority"`
	Assignee    *User    `json:"assignee"`
	CreatedUser User     `json:"createdUser"`
	Created     string   `json:"created"`
	Updated     string   `json:"updated"`
}

type Comment struct {
	ID          int    `json:"id"`
	Content     string `json:"content"`
	CreatedUser User   `json:"createdUser"`
	Created     string `json:"created"`
}
