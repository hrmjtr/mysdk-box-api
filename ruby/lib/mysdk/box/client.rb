require "json"
require "net/http"
require "uri"

module MySdk
  module Box
    class Client
      def initialize(base_url:, access_token:)
        @base_url = base_url.chomp("/")
        @access_token = access_token
      end

      def current_user                   = get("/users/me")
      def user(id)                       = get("/users/#{id}")
      def folder(id)                     = get("/folders/#{id}")
      def folder_items(id, params = {})  = get("/folders/#{id}/items", params)
      def folder_collaborations(id)      = get("/folders/#{id}/collaborations")
      def file(id)                       = get("/files/#{id}")
      def file_comments(id)              = get("/files/#{id}/comments")
      def search(query, params = {})     = get("/search", params.merge(query: query))

      private

      def get(path, params = {})
        uri = URI.parse(@base_url + path)
        uri.query = URI.encode_www_form(params) unless params.empty?
        headers = { "Authorization" => "Bearer #{@access_token}" }
        parse_response(Net::HTTP.get_response(uri, headers))
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
