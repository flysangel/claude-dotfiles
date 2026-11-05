# Data Model: 個人化 SDD 工具組

## 部署紀錄

位置：`~/.claude/.dotfiles/manifest.json`，只存在本機。

| 欄位 | 說明 |
|---|---|
| `status` | `in_progress` 或 `complete` |
| `repo_commit` | 部署時的 commit，僅供查看 |
| `entries[]` | 每個受管檔案一筆 |
| `entries[].path` | 相對於 `~/.claude/` 的路徑，使用 `/` 分隔 |
| `entries[].sha256` | 部署內容的雜湊值 |
| `entries[].original` | 部署前的狀態：`absent`，或備份的相對路徑與雜湊值 |

狀態：沒有紀錄 → `in_progress` → `complete` → 解除部署後刪除紀錄。

規則：
- 開始複製前先寫入 `in_progress`；中斷後可重新部署或解除部署。
- 再次部署時，`original` 維持第一次的值，還原目標才會是最初的狀態。
- 本機內容與 `sha256` 不同時視為本機已修改，覆蓋或還原前先另外備份。

備份位置：`~/.claude/.dotfiles/backups/`。

## 導入紀錄

位置：目標專案的 `.specify/sdd-init.json`，隨專案入庫。

| 欄位 | 說明 |
|---|---|
| `speckit_version` | 實際安裝的版本 |
| `script` | `sh` 或 `ps` |
| `created[]` | 導入時建立的檔案：相對路徑與雜湊值 |
| `skipped[]` | 因已存在而未建立的檔案 |

移除規則：只刪除 `created` 中雜湊值相符的檔案，包含未修改的 `constitution.md` 範本；已修改的檔案保留並回報。`specs/` 不受影響。

## Constitution 草稿

由 `sdd-derive` 在對話中提出，確認前不寫檔。

| 欄位 | 說明 |
|---|---|
| 原則內容 | 規則本身 |
| 類型 | `已經這樣做` 或 `應該這樣做`；後者須維護者確認 |
| 依據 | 專案內的檔案路徑 |
| 狀態 | `有依據` 或 `待確認` |

## 候選功能

| 欄位 | 說明 |
|---|---|
| 名稱與描述 | 從使用者角度描述 |
| 依據 | 專案內的檔案路徑 |
| 選取 | 維護者選擇後才產生 spec |

## 決策摘要

由 `sdd-grill` 產生；維護者確認前不寫入 constitution 或 spec，中途的內容存在「討論進度」。

| 分類 | 去向 |
|---|---|
| 已決定 | 確認後寫入 constitution 或 spec |
| 已延後 | 記錄在 spec 的 Assumptions |
| 留給 plan | 不寫入 constitution，可附在 spec 的備註供 plan 參考 |

## 討論進度

位置：目標專案的 `.specify/sdd-grill-progress.md`，只存在本機，不入庫。

內容與決策摘要相同，另記錄目前討論到的功能。狀態：不存在 → 討論中 → 文件寫入成功後刪除。重新開始時也會刪除。
