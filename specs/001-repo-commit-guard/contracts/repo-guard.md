# Contract: 入庫防護

取代 002 的 `contracts/allowlist.md`。

```text
uv run tools/repo_guard.py [--staged | --all | --history | --commit-msg <file> | --status | --install-hook | --uninstall-hook]
```

| 模式 | 檢查內容 | 使用時機 |
|---|---|---|
| `--staged`（預設） | 暫存區的檔案、作者與提交者 email | `pre-commit` hook |
| `--commit-msg <file>` | commit 訊息內容 | `commit-msg` hook |
| `--all` | 所有已追蹤檔案 | 手動 |
| `--history` | 所有已追蹤檔案，加上 `git rev-list --all` 每個 commit 的身分、訊息與引入的檔案版本 | 公開前 |
| `--status` | 不檢查，回報啟用狀態 | 手動 |
| `--install-hook` | 安裝兩個 hook，重複執行結果相同；已有其他 hook 時不覆蓋 | 新 clone |
| `--uninstall-hook` | 只移除由此工具安裝的 hook，含 002 版本 | 手動 |

## 檢查規則

| 類型 | 內容 |
|---|---|
| `allowlist` | 路徑不在 `.repo-allowlist`；刪除的檔案不檢查 |
| `binary` | 檔案含 NUL，無法掃描 |
| `home-path` | Windows 與 Linux 的個人家目錄絕對路徑 |
| `git-email` | 全域 git `user.email` 的值 |
| `email` | noreply 與保留網域以外的 email |
| `secret` | 常見憑證與 token 格式 |
| `identity` | 本機識別清單的內容，比對檔案內容、commit 訊息，以及作者與提交者名稱 |
| `author`、`committer` | 不是 noreply 地址 |

## 輸出

每個違規一行：位置、類型、修正方向。可豁免的違規另外顯示指紋，並提示如何記錄例外。**不得顯示被比對到的內容。**

`--history` 另外顯示 commit 的前 12 碼，最後一行明確寫出 `通過` 或 `不通過`。

`--status` 第一行是 `enabled`、`not-installed` 或 `unverified`，之後列出 `core.hooksPath` 是否設定、本機識別清單是否存在，以及作者 email 是否為 noreply。

## 結束碼

| 碼 | 意義 |
|---|---|
| 0 | 通過，或 `--status` 正常回報 |
| 1 | 有違規，或 hook 安裝被既有 hook 擋下 |
| 3 | 無法完成檢查，例如白名單遺失、例外檔格式錯誤，或 `--history` 時本機識別清單不存在或沒有內容；視為未通過 |

本機識別清單不存在或沒有內容時，`--staged`、`--commit-msg` 與 `--all` 只提醒，不影響結束碼。

## Hook

寫入 repo 自己的 hooks 目錄（`git rev-parse --git-common-dir` 之下），不寫入 `core.hooksPath` 指向的目錄。內容不含絕對路徑，使用 LF。hook 找不到 `uv` 或工具時，commit 會被阻止。
