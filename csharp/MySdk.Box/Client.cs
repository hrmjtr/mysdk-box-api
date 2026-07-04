using System.Text.Json;

namespace MySdk.Box;

public class Client
{
    private static readonly JsonSerializerOptions JsonOptions =
        new() { PropertyNameCaseInsensitive = true };

    private readonly HttpClient _http;
    private readonly string _baseUrl;
    private readonly string _apiKey;

    public Client(string baseUrl, string apiKey, HttpClient? http = null)
    {
        _baseUrl = baseUrl.TrimEnd('/');
        _apiKey = apiKey;
        _http = http ?? new HttpClient();
    }

    public Task<Space> GetSpaceAsync() => GetAsync<Space>("/space");
    public Task<List<Project>> GetProjectsAsync() => GetAsync<List<Project>>("/projects");
    public Task<Project> GetProjectAsync(string idOrKey) => GetAsync<Project>($"/projects/{idOrKey}");
    public Task<List<Issue>> GetIssuesAsync(IReadOnlyDictionary<string, string>? query = null) => GetAsync<List<Issue>>("/issues", query);
    public Task<Issue> GetIssueAsync(string idOrKey) => GetAsync<Issue>($"/issues/{idOrKey}");
    public Task<List<Comment>> GetIssueCommentsAsync(string idOrKey) => GetAsync<List<Comment>>($"/issues/{idOrKey}/comments");
    public Task<List<User>> GetUsersAsync() => GetAsync<List<User>>("/users");
    public Task<List<Status>> GetStatusesAsync() => GetAsync<List<Status>>("/statuses");
    public Task<List<Priority>> GetPrioritiesAsync() => GetAsync<List<Priority>>("/priorities");

    private async Task<T> GetAsync<T>(string path, IReadOnlyDictionary<string, string>? query = null)
    {
        var parameters = new List<string> { $"apiKey={Uri.EscapeDataString(_apiKey)}" };
        if (query != null)
        {
            foreach (var (key, value) in query)
                parameters.Add($"{Uri.EscapeDataString(key)}={Uri.EscapeDataString(value)}");
        }
        var url = $"{_baseUrl}{path}?{string.Join("&", parameters)}";

        using var response = await _http.GetAsync(url);
        var body = await response.Content.ReadAsStringAsync();

        if (!response.IsSuccessStatusCode)
            throw new BoxHttpException((int)response.StatusCode, body);
        if (string.IsNullOrWhiteSpace(body))
            throw new BoxEmptyResponseException();

        // まず JSON として正しいかを確認し(壊れていれば BoxParseException)、
        // その後に想定した型へ変換する(形が違えば BoxUnexpectedResponseException)。
        JsonDocument document;
        try
        {
            document = JsonDocument.Parse(body);
        }
        catch (JsonException e)
        {
            throw new BoxParseException(e.Message, e);
        }

        using (document)
        {
            try
            {
                var value = document.Deserialize<T>(JsonOptions);
                return value ?? throw new BoxUnexpectedResponseException("response is JSON null");
            }
            catch (JsonException e)
            {
                throw new BoxUnexpectedResponseException(e.Message, e);
            }
        }
    }
}
