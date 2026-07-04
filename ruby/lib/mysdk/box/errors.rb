module MySdk
  module Box
    # すべてのエラーの基底クラス。rescue MySdk::Box::Error でまとめて捕捉できる。
    class Error < StandardError; end

    # HTTP ステータスコードが 2xx 以外
    class HttpError < Error
      attr_reader :status, :body

      def initialize(status:, body:)
        @status = status
        @body = body
        super("HTTP error: status=#{status}")
      end
    end

    # HTTP 200 だが Body が空
    class EmptyResponseError < Error; end

    # JSON として解釈できない(壊れた JSON、途中で切れた JSON など)
    class ParseError < Error; end

    # JSON としては正しいが、想定した形(オブジェクトまたは配列)でない
    class UnexpectedResponseError < Error; end
  end
end
