require "json"
require "net/http"
require "uri"

module MySdk
  module Box
    class Client
      def initialize(base_url:, api_key:)
        @base_url = base_url.chomp("/")
        @api_key = api_key
      end

      def space                     = get("/space")
      def projects                  = get("/projects")
      def project(id_or_key)        = get("/projects/#{id_or_key}")
      def issues(params = {})       = get("/issues", params)
      def issue(id_or_key)          = get("/issues/#{id_or_key}")
      def issue_comments(id_or_key) = get("/issues/#{id_or_key}/comments")
      def users                     = get("/users")
      def statuses                  = get("/statuses")
      def priorities                = get("/priorities")

      private

      def get(path, params = {})
        uri = URI.parse(@base_url + path)
        uri.query = URI.encode_www_form(params.merge(apiKey: @api_key))
        parse_response(Net::HTTP.get_response(uri))
      end

      def parse_response(response)
        body = response.body.to_s

        unless response.is_a?(Net::HTTPSuccess)
          raise HttpError.new(status: response.code.to_i, body: body)
        end
        raise EmptyResponseError, "response body is empty" if body.strip.empty?

        begin
          data = JSON.parse(body)
        rescue JSON::ParserError => e
          raise ParseError, "failed to parse JSON: #{e.message}"
        end

        unless data.is_a?(Hash) || data.is_a?(Array)
          raise UnexpectedResponseError, "unexpected JSON type: #{data.class}"
        end
        data
      end
    end
  end
end
