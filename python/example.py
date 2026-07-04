import os
import sys

from mysdk_box import (
    Client,
    EmptyResponseError,
    HttpError,
    ParseError,
    UnexpectedResponseError,
)

client = Client(
    base_url=os.environ.get("BOX_BASE_URL", "https://api.box.com/2.0"),
    access_token=os.environ["BOX_ACCESS_TOKEN"],
)

try:
    me = client.current_user()
    print(f"current user: {me['name']} <{me['login']}>")

    root = client.folder("0")
    print(f"\nfolder: {root['name']} (size={root['size']})")

    print("\nitems in folder 0:")
    for item in client.folder_items("0")["entries"]:
        print(f"  [{item['type']}] {item['name']} (id={item['id']})")

    file = client.file("101")
    print(f"\nfile: {file['name']} size={file['size']} sha1={file['sha1']}")

    print("\ncomments on file 101:")
    for comment in client.file_comments("101")["entries"]:
        print(f"  {comment['created_by']['name']}: {comment['message']}")

    print("\ncollaborations on folder 11:")
    for collab in client.folder_collaborations("11")["entries"]:
        print(f"  {collab['accessible_by']['name']}: {collab['role']}")

    print('\nsearch "report":')
    for item in client.search("report")["entries"]:
        print(f"  [{item['type']}] {item['name']}")
except HttpError as e:
    sys.exit(f"HTTP error: status={e.status} body={e.body}")
except EmptyResponseError as e:
    sys.exit(f"empty response: {e}")
except ParseError as e:
    sys.exit(f"JSON parse error: {e}")
except UnexpectedResponseError as e:
    sys.exit(f"unexpected response: {e}")
