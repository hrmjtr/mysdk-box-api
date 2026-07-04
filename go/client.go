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

	baseURL string
	apiKey  string
}

func New(baseURL, apiKey string) *Client {
	return &Client{
		HTTPClient: http.DefaultClient,
		baseURL:    strings.TrimSuffix(baseURL, "/"),
		apiKey:     apiKey,
	}
}

func (c *Client) Space() (Space, error)          { return get[Space](c, "/space", nil) }
func (c *Client) Projects() ([]Project, error)   { return get[[]Project](c, "/projects", nil) }
func (c *Client) Users() ([]User, error)         { return get[[]User](c, "/users", nil) }
func (c *Client) Statuses() ([]Status, error)    { return get[[]Status](c, "/statuses", nil) }
func (c *Client) Priorities() ([]Priority, error) {
	return get[[]Priority](c, "/priorities", nil)
}

func (c *Client) Project(idOrKey string) (Project, error) {
	return get[Project](c, "/projects/"+idOrKey, nil)
}

// params にはクエリパラメータを渡せる(不要なら nil)。
func (c *Client) Issues(params url.Values) ([]Issue, error) {
	return get[[]Issue](c, "/issues", params)
}

func (c *Client) Issue(idOrKey string) (Issue, error) {
	return get[Issue](c, "/issues/"+idOrKey, nil)
}

func (c *Client) IssueComments(idOrKey string) ([]Comment, error) {
	return get[[]Comment](c, "/issues/"+idOrKey+"/comments", nil)
}

func get[T any](c *Client, path string, params url.Values) (T, error) {
	var v T

	query := url.Values{}
	for key, values := range params {
		query[key] = values
	}
	query.Set("apiKey", c.apiKey)

	res, err := c.HTTPClient.Get(c.baseURL + path + "?" + query.Encode())
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
