# Data Model: 授權聲明與一行指令設定

## 設定紀錄

路徑：`~/.config/claude-dotfiles/setup.json`。只存在本機，不入庫。由 `machine_setup.py` 寫入，採原子寫入。

| 欄位 | 型別 | 說明 |
|---|---|---|
| `version` | 整數 | 紀錄格式版本，目前為 `1` |
| `clone` | 字串 | clone 的絕對路徑 |
| `installed_tools` | 字串陣列 | 由一行指令安裝的工具，值為 `uv`、`git`、`claude`；多次執行取聯集 |
| `dev` | 物件或 `null` | 沒做過開發設定時為 `null` |
| `dev.hook_installed` | 布林 | commit 防護是否由一行指令安裝：安裝前 `--status` 第一行為 `not-installed` 且安裝成功才為真；原本就已啟用時為假；已為真時重複執行不改變 |
| `dev.email_set` | 字串或 `null` | 一行指令寫入的 email；沿用既有 noreply 地址時為 `null` |
| `dev.previous_email` | 字串或 `null` | 第一次開發設定前，這個 clone 的本機 `user.email`；原本沒有時為 `null` |

規則：

- `dev.previous_email` 只在第一次開發設定時寫入，重複執行不覆蓋，否則會失去真正的原值。
- 紀錄要在對應的變更之前寫入，這樣中斷後仍能還原。
- `clone` 已指向另一個仍存在的目錄時，`install` 停止並回報；目錄已不存在才改寫。
- 紀錄格式錯誤時，`install` 與 `remove` 都停止並回報，不猜測內容。

## 解除時的還原

| 項目 | 條件 | 動作 |
|---|---|---|
| `~/.claude/` | 一律 | 執行 `dotfiles.py undeploy` |
| commit 防護 | `dev.hook_installed` | 執行 `repo_guard.py --uninstall-hook`；別的工具的 hook 不動 |
| 提交身分 | `dev.email_set` 不是 `null` | 目前值等於 `email_set` 才還原為 `previous_email` 或移除；已被使用者改動就保留並回報 |
| 工具與 clone | 一律 | 保留，在摘要列出 |
| 設定紀錄 | 以上都成功 | 刪除；目錄空了也一併移除 |

## 設定流程的狀態

```text
入口：確認作業系統 → 檢查既有工具 → 安裝缺少的工具 → 確認或建立 clone
Python：載入紀錄 → 檢查參數 → 更新 clone（有更新時重新執行一次）→ 開發設定 → 部署 → 摘要
```

任何一步失敗就停止，並指出該步驟。除了部署已有的中斷處理，其餘步驟重新執行都會接續完成，因為每一步都先檢查是否已經完成。
