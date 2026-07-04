import json
import urllib.error
import urllib.parse
import urllib.request

from .errors import EmptyResponseError, HttpError, ParseError, UnexpectedResponseError


class Client:
    def __init__(self, base_url, api_key):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def space(self):
        return self._get("/space")

    def projects(self):
        return self._get("/projects")

    def project(self, id_or_key):
        return self._get(f"/projects/{id_or_key}")

    def issues(self, **params):
        return self._get("/issues", params)

    def issue(self, id_or_key):
        return self._get(f"/issues/{id_or_key}")

    def issue_comments(self, id_or_key):
        return self._get(f"/issues/{id_or_key}/comments")

    def users(self):
        return self._get("/users")

    def statuses(self):
        return self._get("/statuses")

    def priorities(self):
        return self._get("/priorities")

    def _get(self, path, params=None):
        query = dict(params or {})
        query["apiKey"] = self.api_key
        url = f"{self.base_url}{path}?{urllib.parse.urlencode(query)}"

        try:
            with urllib.request.urlopen(url) as response:
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
