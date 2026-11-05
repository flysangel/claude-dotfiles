# Contract: 最小白名單檢查

這是憲章原則 I 在 `001-repo-commit-guard` 完成前的最低防線，由維護者或 Claude 在每次 commit 前手動執行，不會自動攔截。自動攔截、完整歷史掃描與誤判例外由 001 負責。

```text
uv run tools/check_allowlist.py [--staged | --all]
```

- `--staged`（預設）：檢查暫存區，刪除的檔案不檢查。
- `--all`：檢查所有已追蹤的檔案。

## 白名單

`.repo-allowlist` 每行一個 glob，相對於 repo 根目錄，一律使用 `/`；`#` 開頭為註解。初始內容：

```text
.claude/skills/speckit-*/**
.specify/**
specs/**
home/**
tools/**
tests/**
docs/**
.gitattributes
.gitignore
.repo-allowlist
```

## 內容檢查

- 個人家目錄的絕對路徑（Windows 與 Linux）
- `git config --global user.email` 的值，以及 noreply、保留網域以外的 email
- 常見憑證與 token 格式

`tests/fixtures/sample-project/` 內的假憑證允許通過，其他內容檢查照常。`tests/test_check_allowlist.py` 的違規樣本要在執行時組合，不得以完整字串入庫。

## 結果

| 結束碼 | 意義 |
|---|---|
| 0 | 通過 |
| 1 | 有違規，列出檔案、行號與類型，不顯示機密完整值 |
| 3 | 無法完成檢查，例如白名單遺失；視為未通過 |
