# Contract: Spec Kit 導入

入口：手動執行 `/sdd-init`。Skill 在目前專案呼叫內附腳本：

```text
uv run "${CLAUDE_SKILL_DIR}/scripts/sdd_init.py" <init|remove> [--project <path>] [--all]
```

## `init`

1. 已有 `.specify/init-options.json`：回報既有版本後結束，不改動任何內容。
2. 檢查 `uv`、`git`；缺少時說明安裝方式後結束。
3. 取得最新穩定版標籤。
4. 依作業系統選擇 `ps` 或 `sh`，把 Spec Kit 初始化到暫存目錄。
5. 只把目標專案不存在的檔案複製過去，寫入 `.specify/sdd-init.json`；中途失敗則移除這次建立的檔案。
6. 回報版本、建立數、略過的檔案與下一步。

下一步：專案有內容時建議 `sdd-derive`，空專案建議 `sdd-grill`。「有內容」指 `.git` 與 `.claude`、`.specify` 以外還有任何檔案。

## `remove`

依 `.specify/sdd-init.json` 刪除未修改的檔案，包含未修改的 `constitution.md` 範本，並移除紀錄檔與空目錄。已修改的檔案保留並回報，加 `--all` 才一併移除；一律不動 `specs/`。

## 結束碼

| 碼 | 意義 |
|---|---|
| 0 | 完成，或已導入而未改動 |
| 1 | 失敗，專案已回到執行前的狀態 |
| 3 | 缺少前置工具或無法取得版本，未改動專案 |
