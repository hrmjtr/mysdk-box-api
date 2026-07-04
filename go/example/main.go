package main

import (
	"errors"
	"fmt"
	"os"

	"mysdkbox"
)

func main() {
	baseURL := os.Getenv("BOX_BASE_URL")
	if baseURL == "" {
		baseURL = "https://api.box.com/2.0"
	}
	client := mysdkbox.New(baseURL, os.Getenv("BOX_ACCESS_TOKEN"))

	me, err := client.CurrentUser()
	exitIf(err)
	fmt.Printf("current user: %s <%s>\n", me.Name, me.Login)

	root, err := client.Folder("0")
	exitIf(err)
	fmt.Printf("\nfolder: %s (size=%d)\n", root.Name, root.Size)

	items, err := client.FolderItems("0", nil)
	exitIf(err)
	fmt.Println("\nitems in folder 0:")
	for _, item := range items.Entries {
		fmt.Printf("  [%s] %s (id=%s)\n", item.Type, item.Name, item.ID)
	}

	file, err := client.File("101")
	exitIf(err)
	fmt.Printf("\nfile: %s size=%d sha1=%s\n", file.Name, file.Size, file.SHA1)

	comments, err := client.FileComments("101")
	exitIf(err)
	fmt.Println("\ncomments on file 101:")
	for _, comment := range comments.Entries {
		fmt.Printf("  %s: %s\n", comment.CreatedBy.Name, comment.Message)
	}

	collabs, err := client.FolderCollaborations("11")
	exitIf(err)
	fmt.Println("\ncollaborations on folder 11:")
	for _, collab := range collabs.Entries {
		fmt.Printf("  %s: %s\n", collab.AccessibleBy.Name, collab.Role)
	}

	results, err := client.Search("report", nil)
	exitIf(err)
	fmt.Println("\nsearch \"report\":")
	for _, item := range results.Entries {
		fmt.Printf("  [%s] %s\n", item.Type, item.Name)
	}
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
