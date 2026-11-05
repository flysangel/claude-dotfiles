# Contract: 部署指令

```text
uv run tools/dotfiles.py <deploy|undeploy|status> [--target <path>] [--force]
```

`--target` 預設為 `~/.claude/`，測試時指向暫存目錄。

| 指令 | 行為 | 結束碼 |
|---|---|---|
| `deploy` | 將 `home/` 複製到目標；覆蓋前備份；移除 repo 已刪除的受管檔案；重複執行不產生新的備份；完成時提示機器專屬內容要放在 `~/.claude/rules/` | 0 成功；1 失敗；2 有衝突 |
| `undeploy` | 還原部署前狀態並刪除部署紀錄；只處理部署紀錄中的檔案；沒有部署紀錄時不改動並回報 | 0 成功；1 失敗 |
| `status` | 只讀取，回報 `not-deployed`、`clean`、`local-modified`、`repo-ahead` 或 `incomplete` | 0 |

`status` 依序判斷，回報第一個符合的狀態，並列出差異檔案：

1. `not-deployed`：沒有部署紀錄。
2. `incomplete`：紀錄為 `in_progress`。
3. `local-modified`：目標檔案與紀錄的雜湊值不同。
4. `repo-ahead`：`home/` 與紀錄不同。
5. `clean`：都相同。

衝突與保護規則：

- 個人 CLAUDE.md 已存在：備份後取代，並提示備份位置。
- 同名 skill 已存在且不受管：停止並回傳 2；加 `--force` 才會備份後取代。
- `~/.claude/rules/` 和其他未受管內容一律不碰。
- 輸出不得包含被備份檔案的內容。

驗收：解除部署後，受影響檔案與部署前的內容逐位元組相同（SC-002）。
