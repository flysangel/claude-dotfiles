# Contract: 一行指令

## 一行指令

Linux（沒有 `curl` 時，把 `curl -fsSL` 換成 `wget -qO-`）：

```text
curl -fsSL https://raw.githubusercontent.com/flysangel/claude-dotfiles/main/tools/setup.sh | bash
curl -fsSL https://raw.githubusercontent.com/flysangel/claude-dotfiles/main/tools/setup.sh | bash -s -- [選項]
```

Windows PowerShell：

```text
irm https://raw.githubusercontent.com/flysangel/claude-dotfiles/main/tools/setup.ps1 | iex
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/flysangel/claude-dotfiles/main/tools/setup.ps1))) [選項]
```

## 入口選項

| Linux | Windows | 意義 |
|---|---|---|
| `--dir <路徑>` | `-Dir <路徑>` | clone 位置，預設為家目錄下的 `claude-dotfiles` |
| `--dev` | `-Dev` | 同時做開發設定 |
| `--email <地址>` | `-Email <地址>` | 開發設定使用的 GitHub noreply 地址 |
| `--force` | `-Force` | 備份後取代同名且不受管的 skill |

## 入口環境變數

只供測試與公開前驗收使用，不寫在 README 的主要流程。

| 變數 | 意義 |
|---|---|
| `CLAUDE_DOTFILES_REPO` | 改用其他 clone 來源，例如本機路徑；`origin` 比對也改用它 |

公開前驗收時直接執行 clone 內的 `tools/setup.sh` 或 `tools/setup.ps1`；clone 不在預設位置時要加 `--dir` 或 `-Dir`。

## Python 層

```text
uv run <clone>/tools/machine_setup.py install [--dev] [--email <地址>] [--force] [--installed <工具,...>] [--target <目錄>]
uv run <clone>/tools/machine_setup.py remove [--target <目錄>]
```

`install` 由入口呼叫，`remove` 是使用者的解除指令。`--target` 預設為 `~/.claude`，供測試隔離。

## 行為

| 情境 | 結果 |
|---|---|
| 不是 Linux 或 Windows，或用錯入口 | 任何變更前停止，結束碼 1 |
| 既有工具版本過舊 | 安裝任何東西前停止，列出所需版本，結束碼 1 |
| git 無法自動安裝 | 停止，列出手動安裝方式，結束碼 1 |
| 目標目錄已存在且不是這個 repo（比對規則見 research 第 8 節） | 不動它，不執行其中的程式，結束碼 1 |
| 設定紀錄指向另一個仍存在的 clone | 不動它們，提示改用原位置或先解除，結束碼 1 |
| clone 有未提交改動或已分岔 | 不更新也不部署，結束碼 1 |
| `--dev` 但 email 無效或缺少 | 不做開發設定也不部署，結束碼 1 |
| `--dev` 但 hook 被其他工具佔用 | 不覆蓋；仍完成部署，摘要回報，結束碼 1 |
| 同名且不受管的 skill | 沿用部署行為，結束碼 2 |
| 本機識別清單不存在 | 只在 `--dev` 時提示如何建立，不影響結束碼 |

## 輸出

入口每一步一行英文訊息。結束時顯示摘要：

```text
設定完成。
  已安裝工具：uv、git（沒有時顯示「無」）
  repo 位置：<路徑>
  部署結果：已部署 N 個檔案 | 已是最新狀態
  commit 防護：enabled | unverified | not-installed（只在 --dev 時顯示）
待處理：
  - 執行 claude 登入（Claude Code 尚未登入時）
  - 開新的終端機（這次有安裝工具時）
```

失敗時的最後一行指出失敗的步驟與處理方式。輸出不得包含 email 的值。

`remove` 的摘要列出已還原的項目、保留的工具與 clone，以及各工具官方解除安裝說明的連結。

## 結束碼

| 碼 | 意義 |
|---|---|
| 0 | 全部完成 |
| 1 | 有步驟失敗或被拒絕 |
| 2 | 部署因同名 skill 停止，與 `dotfiles.py` 相同 |
| 非零 | Windows 互動視窗內 `iex` 不會結束視窗，以 `throw` 回報；透過 `powershell -Command` 執行時為 1 |
