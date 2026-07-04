$LOAD_PATH.unshift File.expand_path("lib", __dir__)
require "mysdk-box"

client = MySdk::Box::Client.new(
  base_url: ENV.fetch("BOX_BASE_URL"),
  api_key: ENV.fetch("BOX_API_KEY")
)

begin
  space = client.space
  puts "space: #{space["name"]} (#{space["spaceKey"]})"

  puts "\nprojects:"
  client.projects.each do |project|
    puts "  [#{project["projectKey"]}] #{project["name"]}"
  end

  puts "\nissues:"
  client.issues.each do |issue|
    puts "  #{issue["issueKey"]}: #{issue["summary"]} (#{issue.dig("status", "name")})"
  end

  issue_key = "DEMO-1"
  puts "\ncomments on #{issue_key}:"
  client.issue_comments(issue_key).each do |comment|
    puts "  #{comment.dig("createdUser", "name")}: #{comment["content"]}"
  end

  puts "\nusers:      #{client.users.map { |u| u["name"] }.join(", ")}"
  puts "statuses:   #{client.statuses.map { |s| s["name"] }.join(", ")}"
  puts "priorities: #{client.priorities.map { |p| p["name"] }.join(", ")}"
rescue MySdk::Box::HttpError => e
  warn "HTTP error: status=#{e.status} body=#{e.body}"
  exit 1
rescue MySdk::Box::EmptyResponseError => e
  warn "empty response: #{e.message}"
  exit 1
rescue MySdk::Box::ParseError => e
  warn "JSON parse error: #{e.message}"
  exit 1
rescue MySdk::Box::UnexpectedResponseError => e
  warn "unexpected response: #{e.message}"
  exit 1
end
