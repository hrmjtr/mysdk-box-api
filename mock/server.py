#!/usr/bin/env python3
"""サンプル実行用のモック box API サーバー。

使い方:
    python3 mock/server.py [port]   # デフォルトポート: 8793

- apiKey クエリパラメータがないリクエストには 401 を返す。
- /broken/* は、エラー処理の動作確認用に異常なレスポンスを返す。
"""

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

USERS = [
    {"id": 1, "userId": "alice", "name": "Alice", "mailAddress": "alice@example.com"},
    {"id": 2, "userId": "bob", "name": "Bob", "mailAddress": "bob@example.com"},
]

STATUSES = [
    {"id": 1, "name": "Open"},
    {"id": 2, "name": "In Progress"},
    {"id": 3, "name": "Closed"},
]

PRIORITIES = [
    {"id": 1, "name": "High"},
    {"id": 2, "name": "Normal"},
    {"id": 3, "name": "Low"},
]

PROJECTS = [
    {"id": 1, "projectKey": "DEMO", "name": "Demo Project", "archived": False},
    {"id": 2, "projectKey": "SUB", "name": "Sub Project", "archived": True},
]

ISSUES = [
    {
        "id": 101,
        "issueKey": "DEMO-1",
        "summary": "First issue",
        "description": "This is the first demo issue.",
        "status": STATUSES[0],
        "priority": PRIORITIES[1],
        "assignee": USERS[0],
        "createdUser": USERS[1],
        "created": "2026-07-01T09:00:00Z",
        "updated": "2026-07-02T10:30:00Z",
    },
    {
        "id": 102,
        "issueKey": "DEMO-2",
        "summary": "Second issue",
        "description": None,
        "status": STATUSES[1],
        "priority": PRIORITIES[0],
        "assignee": None,
        "createdUser": USERS[0],
        "created": "2026-07-03T08:15:00Z",
        "updated": "2026-07-03T08:15:00Z",
    },
]

COMMENTS = [
    {"id": 1001, "content": "Looks good.", "createdUser": USERS[0], "created": "2026-07-02T11:00:00Z"},
    {"id": 1002, "content": "Fixed.", "createdUser": USERS[1], "created": "2026-07-02T12:00:00Z"},
]

ROUTES = {
    "/space": {"spaceKey": "demo", "name": "Demo Space"},
    "/projects": PROJECTS,
    "/projects/1": PROJECTS[0],
    "/projects/DEMO": PROJECTS[0],
    "/projects/2": PROJECTS[1],
    "/projects/SUB": PROJECTS[1],
    "/issues": ISSUES,
    "/issues/101": ISSUES[0],
    "/issues/DEMO-1": ISSUES[0],
    "/issues/102": ISSUES[1],
    "/issues/DEMO-2": ISSUES[1],
    "/issues/101/comments": COMMENTS,
    "/issues/DEMO-1/comments": COMMENTS,
    "/users": USERS,
    "/statuses": STATUSES,
    "/priorities": PRIORITIES,
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        path = url.path

        # 異常系: エラー処理の動作確認用
        if path == "/broken/empty":
            return self._send(200, "")
        if path == "/broken/truncated":
            return self._send(200, '{"id": 1, "name": "trunc')
        if path == "/broken/scalar":
            return self._send(200, "42")
        if path == "/broken/not-json":
            return self._send(200, "<html>maintenance</html>")
        if path == "/broken/http-error":
            return self._send(500, '{"errors": [{"message": "internal error"}]}')

        if "apiKey" not in parse_qs(url.query):
            return self._send(401, '{"errors": [{"message": "api key is required"}]}')

        data = ROUTES.get(path)
        if data is None:
            return self._send(404, '{"errors": [{"message": "not found"}]}')
        self._send(200, json.dumps(data))

    def _send(self, status, body):
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} {fmt % args}")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8793
    print(f"mock box API server: http://localhost:{port}")
    HTTPServer(("localhost", port), Handler).serve_forever()
