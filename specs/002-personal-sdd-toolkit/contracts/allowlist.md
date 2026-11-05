# Contract: 最小白名單檢查

這是憲章原則 I 在 `001-repo-commit-guard` 完成前的最低防線，透過 git pre-commit hook 在每次 commit 前自動執行。每個 clone 都要安裝一次，也能被 `--no-verify` 略過。commit 訊息檢查、完整歷史掃描與誤判例外由 001 負責。

```text
uv run tools/check_allowlist.py [--staged | --all | --install-hook | --uninstall-hook]
```

- `--staged`（預設）：檢查暫存區，刪除的檔案不檢查。
- `--all`：檢查所有已追蹤的檔案。
- `--install-hook`：在 `.git/hooks/pre-commit` 寫入執行 `--staged` 的 hook，內容不含絕對路徑，重複執行結果相同；已有其他 hook 時不覆蓋，回傳 1。
- `--uninstall-hook`：只移除由此指令安裝的 hook。

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

## 作者檢查

`--staged` 用 `git var` 取得這次 commit 的作者與提交者 email，兩者都必須是 noreply 地址（`noreply@` 開頭，或結尾為 `@users.noreply.github.com`）。不通過時提示如何設定此 repo 的 `user.email`。

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
