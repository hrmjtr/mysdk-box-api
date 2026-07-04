#!/usr/bin/env python3
"""サンプル実行用のモック Box API サーバー。

使い方:
    python3 mock/server.py [port]   # デフォルトポート: 8793

- Authorization: Bearer ヘッダーがないリクエストには 401 を返す。
- /broken/* は、エラー処理の動作確認用に異常なレスポンスを返す。
"""

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

ALICE = {"type": "user", "id": "1", "name": "Alice Example", "login": "alice@example.com"}
BOB = {"type": "user", "id": "2", "name": "Bob Example", "login": "bob@example.com"}

ROOT_FOLDER = {
    "type": "folder",
    "id": "0",
    "name": "All Files",
    "size": 125512,
    "item_status": "active",
    "created_at": None,          # Box の仕様: ルートフォルダの created_at は null
    "modified_at": "2026-07-03T08:15:00Z",
}

DOCS_FOLDER = {
    "type": "folder",
    "id": "11",
    "name": "Documents",
    "size": 45512,
    "item_status": "active",
    "created_at": "2026-07-01T09:00:00Z",
    "modified_at": "2026-07-02T10:30:00Z",
}

REPORT_FILE = {
    "type": "file",
    "id": "101",
    "name": "report.pdf",
    "size": 80000,
    "sha1": "85136c79cbf9fe36bb9d05d0639c70c265c18d37",
    "created_at": "2026-07-01T09:30:00Z",
    "modified_at": "2026-07-02T11:45:00Z",
}

NOTES_FILE = {
    "type": "file",
    "id": "102",
    "name": "notes.txt",
    "size": 512,
    "sha1": "2aae6c35c94fcfb415dbe95f408b9ce91ee846ed",
    "created_at": "2026-07-03T08:15:00Z",
    "modified_at": "2026-07-03T08:15:00Z",
}

COMMENTS = [
    {"type": "comment", "id": "1001", "message": "Looks good.", "created_by": ALICE, "created_at": "2026-07-02T11:00:00Z"},
    {"type": "comment", "id": "1002", "message": "Fixed the numbers.", "created_by": BOB, "created_at": "2026-07-02T12:00:00Z"},
]

COLLABORATIONS = [
    {"type": "collaboration", "id": "9001", "role": "editor", "accessible_by": BOB},
]


def collection(entries):
    """Box の一覧レスポンス形式(コレクション)に包む。"""
    return {"total_count": len(entries), "entries": entries, "offset": 0, "limit": 100}


def error_body(status, code, message):
    return json.dumps({"type": "error", "status": status, "code": code, "message": message})


ROUTES = {
    "/users/me": ALICE,
    "/users/1": ALICE,
    "/users/2": BOB,
    "/folders/0": ROOT_FOLDER,
    "/folders/11": DOCS_FOLDER,
    "/folders/0/items": collection([DOCS_FOLDER, REPORT_FILE]),
    "/folders/11/items": collection([NOTES_FILE]),
    "/folders/0/collaborations": collection([]),
    "/folders/11/collaborations": collection(COLLABORATIONS),
    "/files/101": REPORT_FILE,
    "/files/102": NOTES_FILE,
    "/files/101/comments": collection(COMMENTS),
    "/files/102/comments": collection([]),
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        path = url.path

        # 異常系: エラー処理の動作確認用(認証不要)
        if path == "/broken/empty":
            return self._send(200, "")
        if path == "/broken/truncated":
            return self._send(200, '{"id": "1", "name": "trunc')
        if path == "/broken/scalar":
            return self._send(200, "42")
        if path == "/broken/not-json":
            return self._send(200, "<html>maintenance</html>")
        if path == "/broken/http-error":
            return self._send(500, error_body(500, "internal_server_error", "internal error"))

        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return self._send(401, error_body(401, "unauthorized", "Access token is missing or invalid"))

        if path == "/search":
            if "query" not in parse_qs(url.query):
                return self._send(400, error_body(400, "bad_request", "query is required"))
            return self._send(200, json.dumps(collection([REPORT_FILE, DOCS_FOLDER])))

        data = ROUTES.get(path)
        if data is None:
            return self._send(404, error_body(404, "not_found", "not found"))
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
    print(f"mock Box API server: http://localhost:{port}")
    HTTPServer(("localhost", port), Handler).serve_forever()
