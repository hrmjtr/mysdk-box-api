using MySdk.Box;

var client = new Client(
    baseUrl: Environment.GetEnvironmentVariable("BOX_BASE_URL")!,
    apiKey: Environment.GetEnvironmentVariable("BOX_API_KEY")!);

try
{
    var space = await client.GetSpaceAsync();
    Console.WriteLine($"space: {space.Name} ({space.SpaceKey})");

    Console.WriteLine("\nprojects:");
    foreach (var project in await client.GetProjectsAsync())
        Console.WriteLine($"  [{project.ProjectKey}] {project.Name}");

    Console.WriteLine("\nissues:");
    foreach (var issue in await client.GetIssuesAsync())
        Console.WriteLine($"  {issue.IssueKey}: {issue.Summary} ({issue.Status.Name})");

    var issueKey = "DEMO-1";
    Console.WriteLine($"\ncomments on {issueKey}:");
    foreach (var comment in await client.GetIssueCommentsAsync(issueKey))
        Console.WriteLine($"  {comment.CreatedUser.Name}: {comment.Content}");

    var users = await client.GetUsersAsync();
    var statuses = await client.GetStatusesAsync();
    var priorities = await client.GetPrioritiesAsync();
    Console.WriteLine($"\nusers:      {string.Join(", ", users.Select(u => u.Name))}");
    Console.WriteLine($"statuses:   {string.Join(", ", statuses.Select(s => s.Name))}");
    Console.WriteLine($"priorities: {string.Join(", ", priorities.Select(p => p.Name))}");
}
catch (BoxHttpException e)
{
    Console.Error.WriteLine($"HTTP error: status={e.StatusCode} body={e.Body}");
    Environment.Exit(1);
}
catch (BoxEmptyResponseException e)
{
    Console.Error.WriteLine($"empty response: {e.Message}");
    Environment.Exit(1);
}
catch (BoxParseException e)
{
    Console.Error.WriteLine($"JSON parse error: {e.Message}");
    Environment.Exit(1);
}
catch (BoxUnexpectedResponseException e)
{
    Console.Error.WriteLine($"unexpected response: {e.Message}");
    Environment.Exit(1);
}
