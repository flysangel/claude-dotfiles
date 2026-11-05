# 驗收情境：sdd-init

把 `home/skills/sdd-init/` 複製到暫存測試專案的 `.claude/skills/`，再於該專案執行 `/sdd-init`。

| # | 準備 | 預期 |
|---|---|---|
| 1 | 空資料夾 | 回報最新穩定版，`speckit-*` skill 存在，`.git` 已建立且沒有 commit，建議 `sdd-grill` |
| 2 | 含 `README.md` 的資料夾 | `README.md` 不變，建議 `sdd-derive` |
| 3 | 已導入，且 constitution 已修改 | 沒有任何檔案改動，也沒有升級 |
| 4 | 無法連線 | 說明原因，結束碼 3，專案沒有新檔案 |
| 5 | 任一成功導入 | 能得知安裝的版本，`.specify/sdd-init.json` 也記錄了版本 |

另外確認：

- `.specify/scripts/` 符合目前的作業系統。
- `/sdd-init remove` 會刪除未修改的檔案，保留已修改的檔案並回報。
- 模型不會自行觸發這個 skill。
