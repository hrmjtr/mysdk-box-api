class BoxError(Exception):
    """すべてのエラーの基底クラス。except BoxError でまとめて捕捉できる。"""


class HttpError(BoxError):
    """HTTP ステータスコードが 2xx 以外"""

    def __init__(self, status, body):
        super().__init__(f"HTTP error: status={status}")
        self.status = status
        self.body = body


class EmptyResponseError(BoxError):
    """HTTP 200 だが Body が空"""


class ParseError(BoxError):
    """JSON として解釈できない(壊れた JSON、途中で切れた JSON など)"""


class UnexpectedResponseError(BoxError):
    """JSON としては正しいが、想定した形(オブジェクトまたは配列)でない"""
