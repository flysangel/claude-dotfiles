# Data Model: 持續整合測試與 E2E 測試

## E2E 階段結果

每個階段結束時，驅動腳本輸出一行，並附加到 job summary：

```text
E2E <環境> <階段> <PASS|FAIL|UNVERIFIED> <說明>
```

| 欄位 | 值 |
|---|---|
| 環境 | `ubuntu`、`fedora`、`arch`、`minimum`、`windows`，公開後另有 `ubuntu-public`、`windows-public` |
| 階段 | `setup`、`rerun`、`dev`、`remove`、`refuse`；另有項目 `setup-git-install`，只在 Windows 回報，winget 不可用時為 `UNVERIFIED` |
| 結果 | `PASS`；`FAIL`；`UNVERIFIED` 表示該項在這個環境無法驗證 |
| 說明 | 一句話；失敗時寫原因，下載失敗要寫出來源 |

規則：

- 階段依序執行；前一階段失敗時，後續階段記為 `FAIL`，說明為 `previous stage failed`。
- 任一階段為 `FAIL`，驅動腳本以結束碼 1 結束。`UNVERIFIED` 不影響結束碼，但必須出現在 summary。
- 說明與輸出不得含真實 email；開發設定使用的地址固定為假的 `@users.noreply.github.com` 地址。

## 各階段的判定

| 階段 | 動作 | 通過條件 |
|---|---|---|
| `setup` | 執行一行指令（失敗且為下載錯誤時重試一次） | 結束碼 0；uv、git、Claude Code 都可使用；摘要列出這次安裝的工具，`minimum` 環境應為「無」；`dotfiles.py status` 為 `clean` |
| `rerun` | 再執行一次 | 結束碼 0；部署目錄與 clone 的檔案雜湊不變（Claude Code 自己寫入的檔案除外） |
| `dev` | 加開發選項與假地址，設定提交者名稱後在 clone 實際 commit | 防護為 `enabled`；commit 成功；全域 `user.email` 未被設定 |
| `remove` | 執行解除 | 結束碼 0；設定前放入的 `CLAUDE.md` 與 `rules/` 內容相同；hook 已移除；紀錄已刪除；工具與 clone 仍在 |
| `refuse` | 以 `--dir` 指向一個含有會留下記號程式的普通目錄 | 結束碼非 0；記號沒有出現 |

## 測試群組

| 群組 | 測試 | CI 中必須執行的位置 |
|---|---|---|
| `setup-sh` | `tests/test_setup_scripts.py` 中需要 Linux 的測試 | `unit-linux` |
| `powershell` | `tests/test_setup_scripts_windows.py` 中需要 PowerShell 的測試 | `unit-linux`（PowerShell 7）、`unit-windows`（兩種版本） |

`NonWindowsTests` 不屬於任何群組：它只在非 Windows 的 PowerShell 執行，`unit-linux` 會跑到，但不強制。
