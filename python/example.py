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
    base_url=os.environ["BOX_BASE_URL"],
    api_key=os.environ["BOX_API_KEY"],
)

try:
    space = client.space()
    print(f"space: {space['name']} ({space['spaceKey']})")

    print("\nprojects:")
    for project in client.projects():
        print(f"  [{project['projectKey']}] {project['name']}")

    print("\nissues:")
    for issue in client.issues():
        print(f"  {issue['issueKey']}: {issue['summary']} ({issue['status']['name']})")

    issue_key = "DEMO-1"
    print(f"\ncomments on {issue_key}:")
    for comment in client.issue_comments(issue_key):
        print(f"  {comment['createdUser']['name']}: {comment['content']}")

    print(f"\nusers:      {', '.join(u['name'] for u in client.users())}")
    print(f"statuses:   {', '.join(s['name'] for s in client.statuses())}")
    print(f"priorities: {', '.join(p['name'] for p in client.priorities())}")
except HttpError as e:
    sys.exit(f"HTTP error: status={e.status} body={e.body}")
except EmptyResponseError as e:
    sys.exit(f"empty response: {e}")
except ParseError as e:
    sys.exit(f"JSON parse error: {e}")
except UnexpectedResponseError as e:
    sys.exit(f"unexpected response: {e}")
