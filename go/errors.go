package mysdkbox

import (
	"errors"
	"fmt"
)

// HTTP 200 だが Body が空。errors.Is(err, ErrEmptyResponse) で判定する。
var ErrEmptyResponse = errors.New("mysdkbox: response body is empty")

// HTTP ステータスコードが 2xx 以外
type HTTPError struct {
	StatusCode int
	Body       string
}

func (e *HTTPError) Error() string {
	return fmt.Sprintf("mysdkbox: HTTP error: status=%d", e.StatusCode)
}

// JSON として解釈できない(壊れた JSON、途中で切れた JSON など)
type ParseError struct {
	Err  error
	Body string
}

func (e *ParseError) Error() string {
	return fmt.Sprintf("mysdkbox: failed to parse JSON: %v", e.Err)
}

func (e *ParseError) Unwrap() error { return e.Err }

// JSON としては正しいが、想定した形でない
type UnexpectedResponseError struct {
	Err  error
	Body string
}

func (e *UnexpectedResponseError) Error() string {
	return fmt.Sprintf("mysdkbox: unexpected response: %v", e.Err)
}

func (e *UnexpectedResponseError) Unwrap() error { return e.Err }
