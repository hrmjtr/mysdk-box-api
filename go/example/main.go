package main

import (
	"errors"
	"fmt"
	"os"
	"strings"

	"mysdkbox"
)

func main() {
	client := mysdkbox.New(os.Getenv("BOX_BASE_URL"), os.Getenv("BOX_API_KEY"))

	space, err := client.Space()
	exitIf(err)
	fmt.Printf("space: %s (%s)\n", space.Name, space.SpaceKey)

	projects, err := client.Projects()
	exitIf(err)
	fmt.Println("\nprojects:")
	for _, p := range projects {
		fmt.Printf("  [%s] %s\n", p.ProjectKey, p.Name)
	}

	issues, err := client.Issues(nil)
	exitIf(err)
	fmt.Println("\nissues:")
	for _, i := range issues {
		fmt.Printf("  %s: %s (%s)\n", i.IssueKey, i.Summary, i.Status.Name)
	}

	issueKey := "DEMO-1"
	comments, err := client.IssueComments(issueKey)
	exitIf(err)
	fmt.Printf("\ncomments on %s:\n", issueKey)
	for _, c := range comments {
		fmt.Printf("  %s: %s\n", c.CreatedUser.Name, c.Content)
	}

	users, err := client.Users()
	exitIf(err)
	statuses, err := client.Statuses()
	exitIf(err)
	priorities, err := client.Priorities()
	exitIf(err)
	fmt.Printf("\nusers:      %s\n", join(users, func(u mysdkbox.User) string { return u.Name }))
	fmt.Printf("statuses:   %s\n", join(statuses, func(s mysdkbox.Status) string { return s.Name }))
	fmt.Printf("priorities: %s\n", join(priorities, func(p mysdkbox.Priority) string { return p.Name }))
}

// エラー種別ごとの分岐の書き方を示すためのヘルパー
func exitIf(err error) {
	if err == nil {
		return
	}

	var httpErr *mysdkbox.HTTPError
	var parseErr *mysdkbox.ParseError
	var unexpectedErr *mysdkbox.UnexpectedResponseError
	switch {
	case errors.As(err, &httpErr):
		fmt.Fprintf(os.Stderr, "HTTP error: status=%d body=%s\n", httpErr.StatusCode, httpErr.Body)
	case errors.Is(err, mysdkbox.ErrEmptyResponse):
		fmt.Fprintln(os.Stderr, "empty response")
	case errors.As(err, &parseErr):
		fmt.Fprintf(os.Stderr, "JSON parse error: %v\n", parseErr.Err)
	case errors.As(err, &unexpectedErr):
		fmt.Fprintf(os.Stderr, "unexpected response: %v\n", unexpectedErr.Err)
	default:
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
	}
	os.Exit(1)
}

func join[T any](items []T, name func(T) string) string {
	names := make([]string, len(items))
	for i, item := range items {
		names[i] = name(item)
	}
	return strings.Join(names, ", ")
}
