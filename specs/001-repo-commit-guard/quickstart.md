# Quickstart: 驗證入庫防護

每一段都要在 Windows 與 Linux 各跑一次才算完成；Windows 隨 002 的 T040 進行。指令介面見 [contracts/](contracts/)。

## 前置條件

- 已安裝 `uv`、`git`
- 已將此 repo 的 `user.email` 設為 noreply 地址
- 在 repo 根目錄執行

## 1. 自動化測試

```text
uv run -m unittest discover -s tests
```

預期：全部通過。

## 2. 啟用（US1）

1. 記下開始時間，執行 `uv run tools/repo_guard.py --install-hook`，再執行一次。
2. 執行 `uv run tools/repo_guard.py --status`。

預期：1 分鐘內完成（SC-006）；重複安裝沒有變化；未設定 `core.hooksPath` 時回報 `enabled`，有設定時回報 `unverified`。

## 3. Commit 防護（US1、US2）

每項都在此 repo 暫存後實際 `git commit`，確認被擋下，再還原：

| 情境 | 預期 |
|---|---|
| 白名單外的檔案 | 阻止，列出檔案 |
| 白名單內、含假 token | 阻止，有行號與指紋，不顯示 token |
| 白名單內、含個人家目錄路徑 | 阻止 |
| commit 訊息含非 noreply 的 email | 阻止 |
| 暫時改用非 noreply 的 `user.email` | 阻止，並提示如何修正 |
| 乾淨的內容 | 正常完成，等待增加不超過 2 秒（SC-003） |

## 4. 誤判例外

1. 暫存會被誤判的一行內容，記下指紋。
2. 依違規訊息在 `.repo-guard-exceptions.json` 加入例外。
3. 確認通過；再改動該行，確認例外失效。

## 5. 本機識別清單

1. 在識別清單加入一個測試字串，暫存含此字串的檔案。
2. 確認被阻止，輸出沒有顯示該字串。
3. 移除測試字串。

## 6. 設定檢視（US4）

```text
uv run tools/review_settings.py
```

預期：`~/.claude/settings.json` 的每個頂層項目都有分類（SC-008），輸出不含任何設定值，原始檔雜湊值不變，repo 沒有新檔案。

## 7. 公開前的最終確認（US3）

先推到私有 repo，在 Windows 完成 002 的 T040，再於包含 Windows 修正的最新歷史上執行：

```text
uv run tools/repo_guard.py --history
gitleaks git --no-banner --redact
```

預期：兩者都通過（SC-007）。發現真實機密時，依憲章原則 I 視為外洩並更換，不要只刪檔。
