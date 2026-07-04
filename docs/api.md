# box API 仕様(共通ドキュメント)

本リポジトリの 4 実装(Ruby / Python / Go / C#)が対象とする box API の仕様をまとめる。
自分でクライアントを再実装する際は、まずこのドキュメントを読み、
次に実装する言語の解説(`docs/<言語>.md`)を読むとよい。

## 基本仕様

| 項目             | 内容                                             |
|------------------|--------------------------------------------------|
| プロトコル       | HTTPS(モックサーバーは HTTP)                   |
| ベース URL       | スペースごとに異なる(例: `https://example.com/api/v2`)|
| メソッド         | 読み取り系はすべて `GET`                         |
| レスポンス形式   | JSON(キーは camelCase)                         |
| 日時形式         | ISO 8601(例: `2026-07-01T09:00:00Z`)           |
| 文字コード       | UTF-8                                            |

本リポジトリのクライアントは「ベース URL からの相対パス」でエンドポイントを表す。
ベース URL の末尾スラッシュは実装側で取り除いて正規化する。

## 認証

API キーをクエリパラメータ `apiKey` に付けて送る。

```text
GET /projects?apiKey=xxxxxxxx
```

- API キーがない、または不正な場合は `401` が返る。
- ヘッダー認証や OAuth は本リポジトリでは扱わない。

実装上の注意: `apiKey` は毎リクエストに必要なので、クライアント内部の
「クエリ組み立て処理」で必ず付与する(呼び出し側に持たせない)。

## エンドポイント一覧

| 機能             | パス                        | レスポンス            |
|------------------|-----------------------------|-----------------------|
| スペース情報取得 | `GET /space`                | Space オブジェクト    |
| プロジェクト一覧 | `GET /projects`             | Project の配列        |
| プロジェクト情報 | `GET /projects/{idOrKey}`   | Project オブジェクト  |
| 課題一覧         | `GET /issues`               | Issue の配列          |
| 課題情報         | `GET /issues/{idOrKey}`     | Issue オブジェクト    |
| 課題コメント一覧 | `GET /issues/{idOrKey}/comments` | Comment の配列   |
| ユーザー一覧     | `GET /users`                | User の配列           |
| 状態一覧         | `GET /statuses`             | Status の配列         |
| 優先度一覧       | `GET /priorities`           | Priority の配列       |

- `{idOrKey}` は数値 ID(`1`, `101`)とキー(`DEMO`, `DEMO-1`)のどちらでもよい。
- `GET /issues` は `count` などの絞り込み用クエリパラメータを受け付ける。
  本リポジトリの実装はパラメータを素通しする(値の検証はしない)。

## データモデル

### Space

```json
{ "spaceKey": "demo", "name": "Demo Space" }
```

### Project

```json
{ "id": 1, "projectKey": "DEMO", "name": "Demo Project", "archived": false }
```

### User

```json
{ "id": 1, "userId": "alice", "name": "Alice", "mailAddress": "alice@example.com" }
```

### Status / Priority

どちらも同じ形。

```json
{ "id": 1, "name": "Open" }
```

### Issue

```json
{
  "id": 101,
  "issueKey": "DEMO-1",
  "summary": "First issue",
  "description": "This is the first demo issue.",
  "status":   { "id": 1, "name": "Open" },
  "priority": { "id": 2, "name": "Normal" },
  "assignee": { "id": 1, "userId": "alice", "name": "Alice", "mailAddress": "alice@example.com" },
  "createdUser": { "id": 2, "userId": "bob", "name": "Bob", "mailAddress": "bob@example.com" },
  "created": "2026-07-01T09:00:00Z",
  "updated": "2026-07-02T10:30:00Z"
}
```

- `description` と `assignee` は `null` になりうる。
  型付き言語(Go / C#)では null 許容として扱う必要がある。
- 実際の API はここに挙げた以外のフィールドも返す。
  本リポジトリでは「利用頻度が高い最小限」だけを扱い、残りは無視する方針。

### Comment

```json
{
  "id": 1001,
  "content": "Looks good.",
  "createdUser": { "id": 1, "userId": "alice", "name": "Alice", "mailAddress": "alice@example.com" },
  "created": "2026-07-02T11:00:00Z"
}
```

## エラー仕様と分類

box API は **HTTP 200 でも異常なレスポンスを返す場合がある**。
これが本リポジトリのエラー設計の出発点になっている。

実際に起こるパターン:

- Body が空(`Content-Length: 0`)
- JSON が途中で切れている(例: `{"id": 1, "name": "trunc`)
- JSON ではない Body(例: メンテナンス画面の HTML)
- JSON としては正しいが想定外の形(例: 配列を期待したらスカラー値)

これらを正常終了として扱わないため、全実装で次の 4 分類を採用する。

| # | 分類              | 判定条件                             | 例                        |
|---|-------------------|--------------------------------------|---------------------------|
| 1 | HTTP エラー       | ステータスコードが 2xx 以外          | 401, 404, 500             |
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

- [1] では Body も保持する。エラーレスポンスの Body には
  `{"errors": [{"message": "..."}]}` 形式の詳細が入ることが多く、調査に役立つ。
- [4] の「想定した形」の定義は言語で異なる。
  動的型付け(Ruby / Python)ではオブジェクトか配列かだけを確認し、
  静的型付け(Go / C#)では宣言した型に変換できるかで判定する。
  詳細は各言語のドキュメントを参照。

### HTTP エラー時の Body

```json
{ "errors": [{ "message": "api key is required" }] }
```

## モックサーバー

`mock/server.py` は上記仕様を実装したモック。実 API なしでクライアントを開発・検証できる。

```sh
python3 mock/server.py        # http://localhost:8793
```

正常系はエンドポイント一覧の通り。加えて、エラー処理の動作確認用に
**異常なレスポンスを返すエンドポイント** を持つ(`apiKey` 不要)。

| パス                  | レスポンス                          | 期待する分類          |
|-----------------------|-------------------------------------|-----------------------|
| `/broken/http-error`  | 500 + エラー JSON                   | [1] HTTP エラー       |
| `/broken/empty`       | 200 + 空 Body                       | [2] 空レスポンス      |
| `/broken/truncated`   | 200 + 途中で切れた JSON             | [3] JSON パースエラー |
| `/broken/not-json`    | 200 + HTML                          | [3] JSON パースエラー |
| `/broken/scalar`      | 200 + `42`(スカラー値)            | [4] 想定外レスポンス  |

再実装したクライアントは、この 5 つに対して正しい分類のエラーを
返せるかで検収するとよい。
