$LOAD_PATH.unshift File.expand_path("lib", __dir__)
require "mysdk-box"

client = MySdk::Box::Client.new(
  base_url: ENV.fetch("BOX_BASE_URL", "https://api.box.com/2.0"),
  access_token: ENV.fetch("BOX_ACCESS_TOKEN")
)

begin
  me = client.current_user
  puts "current user: #{me["name"]} <#{me["login"]}>"

  root = client.folder("0")
  puts "\nfolder: #{root["name"]} (size=#{root["size"]})"

  puts "\nitems in folder 0:"
  client.folder_items("0")["entries"].each do |item|
    puts "  [#{item["type"]}] #{item["name"]} (id=#{item["id"]})"
  end

  file = client.file("101")
  puts "\nfile: #{file["name"]} size=#{file["size"]} sha1=#{file["sha1"]}"

  puts "\ncomments on file 101:"
  client.file_comments("101")["entries"].each do |comment|
    puts "  #{comment.dig("created_by", "name")}: #{comment["message"]}"
  end

  puts "\ncollaborations on folder 11:"
  client.folder_collaborations("11")["entries"].each do |collab|
    puts "  #{collab.dig("accessible_by", "name")}: #{collab["role"]}"
  end

  puts "\nsearch \"report\":"
  client.search("report")["entries"].each do |item|
    puts "  [#{item["type"]}] #{item["name"]}"
  end
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
