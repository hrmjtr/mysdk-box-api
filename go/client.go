package mysdkbox

import (
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/url"
	"strings"
)

type Client struct {
	// HTTPClient を差し替えるとタイムアウト等を設定できる。
	HTTPClient *http.Client

	baseURL     string
	accessToken string
}

func New(baseURL, accessToken string) *Client {
	return &Client{
		HTTPClient:  http.DefaultClient,
		baseURL:     strings.TrimSuffix(baseURL, "/"),
		accessToken: accessToken,
	}
}

func (c *Client) CurrentUser() (User, error) { return get[User](c, "/users/me", nil) }

func (c *Client) User(id string) (User, error) { return get[User](c, "/users/"+id, nil) }

func (c *Client) Folder(id string) (Folder, error) { return get[Folder](c, "/folders/"+id, nil) }

// params にはクエリパラメータを渡せる(不要なら nil)。
func (c *Client) FolderItems(id string, params url.Values) (Collection[Item], error) {
	return get[Collection[Item]](c, "/folders/"+id+"/items", params)
}

func (c *Client) FolderCollaborations(id string) (Collection[Collaboration], error) {
	return get[Collection[Collaboration]](c, "/folders/"+id+"/collaborations", nil)
}

func (c *Client) File(id string) (File, error) { return get[File](c, "/files/"+id, nil) }

func (c *Client) FileComments(id string) (Collection[Comment], error) {
	return get[Collection[Comment]](c, "/files/"+id+"/comments", nil)
}

func (c *Client) Search(query string, params url.Values) (Collection[Item], error) {
	merged := url.Values{}
	for key, values := range params {
		merged[key] = values
	}
	merged.Set("query", query)
	return get[Collection[Item]](c, "/search", merged)
}

func get[T any](c *Client, path string, params url.Values) (T, error) {
	var v T

	requestURL := c.baseURL + path
	if len(params) > 0 {
		requestURL += "?" + params.Encode()
	}
	req, err := http.NewRequest(http.MethodGet, requestURL, nil)
	if err != nil {
		return v, err
	}
	req.Header.Set("Authorization", "Bearer "+c.accessToken)

	res, err := c.HTTPClient.Do(req)
	if err != nil {
		return v, err
	}
	defer res.Body.Close()

	body, err := io.ReadAll(res.Body)
	if err != nil {
		return v, err
	}

	if res.StatusCode < 200 || res.StatusCode >= 300 {
		return v, &HTTPError{StatusCode: res.StatusCode, Body: string(body)}
	}
	if strings.TrimSpace(string(body)) == "" {
		return v, ErrEmptyResponse
	}

	if err := json.Unmarshal(body, &v); err != nil {
		var typeErr *json.UnmarshalTypeError
		if errors.As(err, &typeErr) {
			return v, &UnexpectedResponseError{Err: err, Body: string(body)}
		}
		return v, &ParseError{Err: err, Body: string(body)}
	}
	return v, nil
}
