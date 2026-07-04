# Box API 仕様(共通ドキュメント)

本リポジトリの 4 実装(Ruby / Python / Go / C#)が対象とする
Box API(Box Platform REST API)の仕様をまとめる。
自分でクライアントを再実装する際は、まずこのドキュメントを読み、
次に実装する言語の解説(`docs/<言語>.md`)を読むとよい。

本リポジトリは Box API の読み取り系のごく一部だけを扱う。
完全なリファレンスは https://developer.box.com/reference/ を参照。

## 基本仕様

| 項目             | 内容                                             |
|------------------|--------------------------------------------------|
| プロトコル       | HTTPS(モックサーバーは HTTP)                   |
| ベース URL       | `https://api.box.com/2.0`                        |
| メソッド         | 読み取り系はすべて `GET`                         |
| レスポンス形式   | JSON(キーは **snake_case**)                    |
| ID               | **文字列**(`"12345"`。数値ではない)            |
| 日時形式         | ISO 8601(例: `2026-07-01T09:00:00Z`)           |
| 文字コード       | UTF-8                                            |

本リポジトリのクライアントは「ベース URL からの相対パス」でエンドポイントを表す。
ベース URL の末尾スラッシュは実装側で取り除いて正規化する。

## 認証

アクセストークンを `Authorization` ヘッダーで送る(Bearer 方式)。

```text
GET /2.0/users/me
Authorization: Bearer <ACCESS_TOKEN>
```

- トークンがない、または不正な場合は `401` が返る。
- 手元で試すだけなら Box 開発者コンソールで発行できる
  Developer Token(有効期限 60 分)が手軽。
  本番用の OAuth 2.0 / JWT / Client Credentials のフローは本リポジトリでは扱わない。

実装上の注意: トークンは毎リクエストに必要なので、クライアント内部の
「リクエスト組み立て処理」で必ずヘッダーに付与する(呼び出し側に持たせない)。

## エンドポイント一覧

| 機能                     | パス                              | レスポンス                  |
|--------------------------|-----------------------------------|-----------------------------|
| 現在のユーザー情報       | `GET /users/me`                   | User                        |
| ユーザー情報             | `GET /users/{id}`                 | User                        |
| フォルダ情報             | `GET /folders/{id}`               | Folder                      |
| フォルダ内アイテム一覧   | `GET /folders/{id}/items`         | Item のコレクション         |
| コラボレーション一覧     | `GET /folders/{id}/collaborations`| Collaboration のコレクション|
| ファイル情報             | `GET /files/{id}`                 | File                        |
| ファイルコメント一覧     | `GET /files/{id}/comments`        | Comment のコレクション      |
| 検索                     | `GET /search?query=...`           | Item のコレクション         |

- ルートフォルダの ID は `"0"` 固定。
- 一覧系は `limit` / `offset` などのクエリパラメータを受け付ける。
  本リポジトリの実装はパラメータを素通しする(値の検証はしない)。
- `/search` は `query` パラメータが必須(ないと `400`)。

## コレクション(一覧レスポンスの共通形式)

Box の一覧系 API は、配列を直接返さず次の形で包んで返す。

```json
{
  "total_count": 2,
  "entries": [ ... ],
  "offset": 0,
  "limit": 100
}
```

- 要素本体は `entries` に入る。ページングは `offset` / `limit` で行う。
- 本リポジトリではこの形をそのまま返す(Ruby / Python は Hash / dict のまま、
  Go / C# は `Collection` 型として定義)。
- `entries` の中身は file / folder / web_link が混在しうる。
  `type` フィールドで見分ける。

## データモデル

実際の API はここに挙げた以外にも多数のフィールドを返す。
本リポジトリでは「利用頻度が高い最小限」だけを扱い、残りは無視する方針。

### User

```json
{ "type": "user", "id": "1", "name": "Alice Example", "login": "alice@example.com" }
```

### Folder

```json
{
  "type": "folder",
  "id": "11",
  "name": "Documents",
  "size": 45512,
  "item_status": "active",
  "created_at": "2026-07-01T09:00:00Z",
  "modified_at": "2026-07-02T10:30:00Z"
}
```

- **ルートフォルダ(id="0")の `created_at` は `null`**。
  型付き言語(Go / C#)では null 許容として扱う必要がある。

### File

```json
{
  "type": "file",
  "id": "101",
  "name": "report.pdf",
  "size": 80000,
  "sha1": "85136c79cbf9fe36bb9d05d0639c70c265c18d37",
  "created_at": "2026-07-01T09:30:00Z",
  "modified_at": "2026-07-02T11:45:00Z"
}
```

### Item(フォルダ内アイテム・検索結果の要素)

`type` / `id` / `name`(+ `size`)だけを共通部分として扱う。
実 API では entries の要素は mini 表現(フィールドが少ない縮約版)で返ることが多い。

### Comment

```json
{
  "type": "comment",
  "id": "1001",
  "message": "Looks good.",
  "created_by": { "type": "user", "id": "1", "name": "Alice Example", "login": "alice@example.com" },
  "created_at": "2026-07-02T11:00:00Z"
}
```

### Collaboration

```json
{
  "type": "collaboration",
  "id": "9001",
  "role": "editor",
  "accessible_by": { "type": "user", "id": "2", "name": "Bob Example", "login": "bob@example.com" }
}
```

`role` は `editor` / `viewer` / `previewer` など。

## エラー仕様と分類

### HTTP エラー時の Body

Box はエラー時に次の形式の JSON を返す。

```json
{
  "type": "error",
  "status": 401,
  "code": "unauthorized",
  "message": "Access token is missing or invalid"
}
```

主なステータス: `400`(パラメータ不正)/ `401`(認証エラー)/
`404`(存在しない ID)/ `429`(レートリミット)。

### 4 分類

API は **HTTP 200 でも異常なレスポンスを返す場合がある**
(プロキシやメンテナンス画面が割り込む、転送が途中で切れる等)。
これが本リポジトリのエラー設計の出発点になっている。

実際に起こるパターン:

- Body が空(`Content-Length: 0`)
- JSON が途中で切れている(例: `{"id": "1", "name": "trunc`)
- JSON ではない Body(例: メンテナンス画面の HTML)
- JSON としては正しいが想定外の形(例: オブジェクトを期待したらスカラー値)

これらを正常終了として扱わないため、全実装で次の 4 分類を採用する。

| # | 分類              | 判定条件                             | 例                        |
|---|-------------------|--------------------------------------|---------------------------|
| 1 | HTTP エラー       | ステータスコードが 2xx 以外          | 401, 404, 429, 500        |
| 2 | 空レスポンス      | 2xx かつ Body が空(空白のみ含む)   | `""`                      |
| 3 | JSON パースエラー | JSON として解釈できない              | 途中で切れた JSON、HTML   |
| 4 | 想定外レスポンス  | JSON だが想定した形でない            | オブジェクト期待で `42`   |

### 判定フロー

全実装がこの順序で判定する。再実装するときもこの順序を守ること
(例: 空 Body を先に JSON パースにかけると、分類 2 と 3 が区別できなくなる)。

```text
レスポンス受信
  ├─ ステータスコードが 2xx 以外 → [1] HTTP エラー(コードと Body を保持)
  ├─ Body が空(strip して空)   → [2] 空レスポンス
  ├─ JSON パース失敗             → [3] JSON パースエラー
  ├─ 想定した形でない            → [4] 想定外レスポンス
  └─ 正常 → パース結果を返す
```

補足:

- [1] では Body も保持する。上記のエラー JSON(`code` / `message`)が
  入っていることが多く、調査に役立つ。
- [4] の「想定した形」の定義は言語で異なる。
  動的型付け(Ruby / Python)ではオブジェクトか配列かだけを確認し、
  静的型付け(Go / C#)では宣言した型に変換できるかで判定する。
  詳細は各言語のドキュメントを参照。

## モックサーバー

`mock/server.py` は上記仕様を実装したモック。実 API なしでクライアントを開発・検証できる。

```sh
python3 mock/server.py        # http://localhost:8793
```

- `Authorization: Bearer ...` ヘッダーがないリクエストには 401 を返す。
- 登録データ: ルートフォルダ(0)の下に Documents フォルダ(11)と
  report.pdf(101)、Documents の下に notes.txt(102)。
  ユーザーは alice(1、`/users/me` の本人)と bob(2)。

加えて、エラー処理の動作確認用に **異常なレスポンスを返すエンドポイント** を持つ
(認証不要)。

| パス                  | レスポンス                          | 期待する分類          |
|-----------------------|-------------------------------------|-----------------------|
| `/broken/http-error`  | 500 + エラー JSON                   | [1] HTTP エラー       |
| `/broken/empty`       | 200 + 空 Body                       | [2] 空レスポンス      |
| `/broken/truncated`   | 200 + 途中で切れた JSON             | [3] JSON パースエラー |
| `/broken/not-json`    | 200 + HTML                          | [3] JSON パースエラー |
| `/broken/scalar`      | 200 + `42`(スカラー値)            | [4] 想定外レスポンス  |

再実装したクライアントは、この 5 つに対して正しい分類のエラーを
返せるかで検収するとよい。
