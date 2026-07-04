using MySdk.Box;

var client = new Client(
    baseUrl: Environment.GetEnvironmentVariable("BOX_BASE_URL") ?? "https://api.box.com/2.0",
    accessToken: Environment.GetEnvironmentVariable("BOX_ACCESS_TOKEN")!);

try
{
    var me = await client.GetCurrentUserAsync();
    Console.WriteLine($"current user: {me.Name} <{me.Login}>");

    var root = await client.GetFolderAsync("0");
    Console.WriteLine($"\nfolder: {root.Name} (size={root.Size})");

    Console.WriteLine("\nitems in folder 0:");
    foreach (var item in (await client.GetFolderItemsAsync("0")).Entries)
        Console.WriteLine($"  [{item.Type}] {item.Name} (id={item.Id})");

    var file = await client.GetFileAsync("101");
    Console.WriteLine($"\nfile: {file.Name} size={file.Size} sha1={file.Sha1}");

    Console.WriteLine("\ncomments on file 101:");
    foreach (var comment in (await client.GetFileCommentsAsync("101")).Entries)
        Console.WriteLine($"  {comment.CreatedBy.Name}: {comment.Message}");

    Console.WriteLine("\ncollaborations on folder 11:");
    foreach (var collab in (await client.GetFolderCollaborationsAsync("11")).Entries)
        Console.WriteLine($"  {collab.AccessibleBy.Name}: {collab.Role}");

    Console.WriteLine("\nsearch \"report\":");
    foreach (var item in (await client.SearchAsync("report")).Entries)
        Console.WriteLine($"  [{item.Type}] {item.Name}");
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
