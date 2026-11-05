# Data Model: 公開 repo 入庫防護

## 白名單

位置：`.repo-allowlist`，入庫。每行一個 glob，相對於 repo 根目錄，使用 `/`；`*` 不跨目錄，`**` 可跨；`#` 開頭為註解。必須列入 `.repo-guard-exceptions.json`。

## 違規

只存在於輸出，不寫入檔案。

| 欄位 | 說明 |
|---|---|
| 位置 | 檔案與行號，歷史檢查再加 commit；或 `commit 作者`、`commit 提交者`、`commit 訊息` |
| 類型 | `allowlist`、`binary`、`home-path`、`email`、`git-email`、`secret`、`identity`、`author`、`committer` |
| 修正方向 | 依類型提供 |
| 指紋 | 該行內容的 SHA-256，用於記錄例外；`allowlist` 與身分類沒有指紋 |

MUST NOT 包含被比對到的內容。

## 誤判例外

位置：`.repo-guard-exceptions.json`，入庫。

```json
{
  "exceptions": [
    {
      "path": "tests/fixtures/sample-project/config/settings.py",
      "kind": "secret",
      "line_sha256": "<該行內容的 SHA-256>",
      "reason": "明顯為假的憑證，用於驗收導出不會外洩"
    }
  ]
}
```

| 欄位 | 規則 |
|---|---|
| `path` | MUST 是單一檔案的完整路徑，不接受 glob |
| `kind` | MUST 是違規類型之一；`allowlist`、`git-email`、`identity`、`author`、`committer` 不可豁免 |
| `line_sha256` | MUST 是 64 位十六進位；`binary` 則是整個檔案的雜湊值 |
| `reason` | MUST 非空 |

格式錯誤時，檢查視為無法完成。內容改變後例外自然失效。例外檔本身也要通過內容檢查。

## 本機識別清單

位置：預設 `~/.config/claude-dotfiles/identity.txt`，不入庫。每行一筆，不分大小寫；空行與 `#` 開頭略過。

## 設定項目分類

只存在於輸出。

| 分類 | 條件 |
|---|---|
| 含機密 | 鍵名像憑證，或值符合憑證規則 |
| 機器專屬 | 值含個人路徑、本機識別資訊，或屬於已知的機器專屬鍵 |
| 可共用 | 屬於已知的安全鍵，且未觸發以上規則 |
| 待判斷 | 其他所有情況 |
