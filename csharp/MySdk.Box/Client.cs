using System.Net.Http.Headers;
using System.Text.Json;

namespace MySdk.Box;

public class Client
{
    // snake_case の JSON キーと PascalCase のプロパティを対応付ける
    private static readonly JsonSerializerOptions JsonOptions =
        new() { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower };

    private readonly HttpClient _http;
    private readonly string _baseUrl;
    private readonly string _accessToken;

    public Client(string baseUrl, string accessToken, HttpClient? http = null)
    {
        _baseUrl = baseUrl.TrimEnd('/');
        _accessToken = accessToken;
        _http = http ?? new HttpClient();
    }

    public Task<User> GetCurrentUserAsync() => GetAsync<User>("/users/me");
    public Task<User> GetUserAsync(string id) => GetAsync<User>($"/users/{id}");
    public Task<Folder> GetFolderAsync(string id) => GetAsync<Folder>($"/folders/{id}");
    public Task<Collection<Item>> GetFolderItemsAsync(string id, IReadOnlyDictionary<string, string>? query = null) => GetAsync<Collection<Item>>($"/folders/{id}/items", query);
    public Task<Collection<Collaboration>> GetFolderCollaborationsAsync(string id) => GetAsync<Collection<Collaboration>>($"/folders/{id}/collaborations");
    public Task<BoxFile> GetFileAsync(string id) => GetAsync<BoxFile>($"/files/{id}");
    public Task<Collection<Comment>> GetFileCommentsAsync(string id) => GetAsync<Collection<Comment>>($"/files/{id}/comments");

    public Task<Collection<Item>> SearchAsync(string query, IReadOnlyDictionary<string, string>? extra = null)
    {
        var merged = new Dictionary<string, string>(extra ?? new Dictionary<string, string>())
        {
            ["query"] = query,
        };
        return GetAsync<Collection<Item>>("/search", merged);
    }

    private async Task<T> GetAsync<T>(string path, IReadOnlyDictionary<string, string>? query = null)
    {
        var url = $"{_baseUrl}{path}";
        if (query is { Count: > 0 })
        {
            var parameters = query.Select(kv =>
                $"{Uri.EscapeDataString(kv.Key)}={Uri.EscapeDataString(kv.Value)}");
            url += $"?{string.Join("&", parameters)}";
        }

        using var request = new HttpRequestMessage(HttpMethod.Get, url);
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _accessToken);

        using var response = await _http.SendAsync(request);
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
