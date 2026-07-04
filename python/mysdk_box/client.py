import json
import urllib.error
import urllib.parse
import urllib.request

from .errors import EmptyResponseError, HttpError, ParseError, UnexpectedResponseError


class Client:
    def __init__(self, base_url, access_token):
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token

    def current_user(self):
        return self._get("/users/me")

    def user(self, user_id):
        return self._get(f"/users/{user_id}")

    def folder(self, folder_id):
        return self._get(f"/folders/{folder_id}")

    def folder_items(self, folder_id, **params):
        return self._get(f"/folders/{folder_id}/items", params)

    def folder_collaborations(self, folder_id):
        return self._get(f"/folders/{folder_id}/collaborations")

    def file(self, file_id):
        return self._get(f"/files/{file_id}")

    def file_comments(self, file_id):
        return self._get(f"/files/{file_id}/comments")

    def search(self, query, **params):
        return self._get("/search", {"query": query, **params})

    def _get(self, path, params=None):
        url = f"{self.base_url}{path}"
        if params:
            url += f"?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {self.access_token}"}
        )

        try:
            with urllib.request.urlopen(request) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            raise HttpError(e.code, e.read().decode("utf-8", "replace")) from e

        return self._parse(body)

    def _parse(self, body):
        if not body.strip():
            raise EmptyResponseError("response body is empty")

        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            raise ParseError(f"failed to parse JSON: {e}") from e

        if not isinstance(data, (dict, list)):
            raise UnexpectedResponseError(
                f"unexpected JSON type: {type(data).__name__}"
            )
        return data
