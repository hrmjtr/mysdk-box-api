namespace MySdk.Box;

/// <summary>すべてのエラーの基底クラス。catch (BoxApiException) でまとめて捕捉できる。</summary>
public class BoxApiException : Exception
{
    public BoxApiException(string message, Exception? inner = null) : base(message, inner) { }
}

/// <summary>HTTP ステータスコードが 2xx 以外</summary>
public class BoxHttpException : BoxApiException
{
    public int StatusCode { get; }
    public string Body { get; }

    public BoxHttpException(int statusCode, string body)
        : base($"HTTP error: status={statusCode}")
    {
        StatusCode = statusCode;
        Body = body;
    }
}

/// <summary>HTTP 200 だが Body が空</summary>
public class BoxEmptyResponseException : BoxApiException
{
    public BoxEmptyResponseException() : base("response body is empty") { }
}

/// <summary>JSON として解釈できない(壊れた JSON、途中で切れた JSON など)</summary>
public class BoxParseException : BoxApiException
{
    public BoxParseException(string message, Exception? inner = null)
        : base($"failed to parse JSON: {message}", inner) { }
}

/// <summary>JSON としては正しいが、想定した形でない</summary>
public class BoxUnexpectedResponseException : BoxApiException
{
    public BoxUnexpectedResponseException(string message, Exception? inner = null)
        : base($"unexpected response: {message}", inner) { }
}
