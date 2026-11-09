# claude-dotfiles

個人化的 Claude Code 設定：一份全域 CLAUDE.md，加上以 [Spec Kit](https://github.com/github/spec-kit) 進行規格驅動開發（SDD）的三個 skill。

| 內容 | 用途 |
|---|---|
| `home/CLAUDE.md` | 所有專案共用的工作偏好 |
| `/sdd-init` | 在專案導入最新穩定版 Spec Kit，或再移除 |
| `sdd-derive` | 從既有專案導出 constitution 與 spec |
| `sdd-grill` | 逐題追問，討論出 constitution 與 spec |

> **目前狀態**：部署與 commit 檢查在 Windows 與 Linux 都已驗收；一行指令在 Linux 與 Windows 都由 CI 的 E2E 驗證，也以公開網址實跑過；Windows 是在 CI 機器上移除既有工具後模擬乾淨環境，尚未在真正的新機器上跑過。macOS 不在支援範圍。

## 安裝

Linux：

```text
curl -fsSL https://raw.githubusercontent.com/flysangel/claude-dotfiles/main/tools/setup.sh | bash
```

沒有 `curl` 時，把 `curl -fsSL` 換成 `wget -qO-`。

Windows PowerShell：

```text
irm https://raw.githubusercontent.com/flysangel/claude-dotfiles/main/tools/setup.ps1 | iex
```

指令會做這些事，重複執行不會有多餘的變更，有新版時會更新：

- 安裝缺少的 uv、git 與 Claude Code。既有的工具不會被更動；版本太舊時會停止並提示。
- 把 repo clone 到家目錄下的 `claude-dotfiles`。
- 把 `home/` 複製到 `~/.claude/`：已有的 `CLAUDE.md` 會先備份，其他內容不受影響。

Linux 的選項接在 `bash -s --` 後面，Windows 要改用另一種寫法才能傳選項：

```text
curl -fsSL https://raw.githubusercontent.com/flysangel/claude-dotfiles/main/tools/setup.sh | bash -s -- --dir <路徑>
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/flysangel/claude-dotfiles/main/tools/setup.ps1))) -Dir <路徑>
```

| Linux | Windows | 用途 |
|---|---|---|
| `--dir <路徑>` | `-Dir <路徑>` | 指定 clone 的位置 |
| `--force` | `-Force` | 同名且不受管的 skill 預設會讓部署停止；確定要取代時使用，原內容會先備份 |
| `--dev` | `-Dev` | 同時做開發設定，見下方 |
| `--email <地址>` | `-Email <地址>` | 開發設定使用的 noreply 地址 |

想先看過腳本再執行：

```text
curl -fsSL https://raw.githubusercontent.com/flysangel/claude-dotfiles/main/tools/setup.sh -o setup.sh && less setup.sh && bash setup.sh
irm https://raw.githubusercontent.com/flysangel/claude-dotfiles/main/tools/setup.ps1 -OutFile setup.ps1; notepad setup.ps1; powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

### 開發設定

要從這個 clone 提交時才需要。加上 `--dev` 與你的 GitHub noreply 地址，會把地址寫入這個 clone 的設定，並安裝 commit 與 push 前的檢查：

```text
curl -fsSL https://raw.githubusercontent.com/flysangel/claude-dotfiles/main/tools/setup.sh | bash -s -- --dev --email "<id>+<帳號>@users.noreply.github.com"
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/flysangel/claude-dotfiles/main/tools/setup.ps1))) -Dev -Email "<id>+<帳號>@users.noreply.github.com"
```

每台機器也要建立一份本機識別清單 `~/.config/claude-dotfiles/identity.txt`，每行一筆你不想公開的內容，例如真實姓名、私人主機名稱。它不會入庫；沒有這份清單時，commit 只會提醒，但 push 與完整檢查不會通過。

### 解除

```text
uv run ~/claude-dotfiles/tools/machine_setup.py remove
```

Windows 把路徑換成 `$HOME\claude-dotfiles\tools\machine_setup.py`；clone 在其他位置時也要換。它會還原 `~/.claude/`，曾做開發設定時也會移除 hook 並還原 email。工具與 clone 會保留，並列出移除方式。

## 日常使用

依專案狀況選擇起點：

| 專案狀況 | 做法 |
|---|---|
| 還沒導入 Spec Kit | 手動執行 `/sdd-init`，它會提示下一步 |
| 新專案或方向未定 | 請 Claude 追問討論，會使用 `sdd-grill` |
| 已有程式碼 | 請 Claude 導出 constitution 與 spec，會使用 `sdd-derive` |

`sdd-grill` 與 `sdd-derive` 都會先等你確認，才寫入文件，並且止於 spec。之後用 Spec Kit 接續：

```text
/speckit-plan → /speckit-tasks → /speckit-implement
```

多個功能時，每個功能各跑一次。Spec Kit 用 `.specify/feature.json` 決定目前處理哪個功能，切換 git 分支不會跟著切換，要換功能時請修改：

```json
{ "feature_directory": "specs/002-example" }
```

`sdd-grill` 中斷後再次執行，可以選擇接續或重新開始。進度存在專案的 `.specify/sdd-grill-progress.md`，不會入庫，所以無法換機器接續。

從專案移除 Spec Kit：

```text
/sdd-init remove        # 刪除未修改的檔案，已修改的保留並回報
/sdd-init remove --all  # 連已修改的檔案一併刪除
```

兩者都不會動 `specs/` 與 `.git`。

## 維護

部署是複製檔案，所以修改 `home/` 後要重新部署。

| 指令 | 用途 |
|---|---|
| `uv run tools/dotfiles.py status` | 查看部署狀態 |
| `uv run tools/dotfiles.py deploy` | 部署或更新，重複執行不會有變更 |
| `uv run tools/dotfiles.py undeploy` | 還原到部署前的狀態 |
| `uv run -m unittest discover -s tests` | 執行測試 |
| `uv run tools/run_trigger_evals.py` | 檢查 skill 是否正確觸發；會呼叫模型並產生費用 |

`status` 的結果：

| 狀態 | 意思 | 處理方式 |
|---|---|---|
| `not-deployed` | 尚未部署 | 執行 `deploy` |
| `clean` | 本機與 repo 相同 | 不用處理 |
| `repo-ahead` | `home/` 有更新 | 執行 `deploy` |
| `local-modified` | `~/.claude/` 內的受管檔案被改過 | 把想保留的改動移到 `home/`，再執行 `deploy`；本機改動會先另存備份 |
| `incomplete` | 上次部署中斷 | 執行 `deploy` 或 `undeploy` |

機器專屬的內容放在 `~/.claude/rules/`，部署不會碰這個目錄，也不會入庫。

## 入庫防護

| 指令 | 用途 |
|---|---|
| `uv run tools/repo_guard.py --status` | 查看防護是否已啟用 |
| `uv run tools/repo_guard.py --all` | 檢查所有已追蹤的檔案 |
| `uv run tools/repo_guard.py --history` | 檢查完整歷史；每次 push 也會自動執行 |
| `uv run tools/review_settings.py` | 判斷 `~/.claude/settings.json` 每個項目能否共用，輸出不含設定值 |

`--status` 回報 `unverified` 表示有設定 `core.hooksPath`，工具無法確認它會不會轉交；用一個會被擋下的 commit 實際試過就能確定。

被誤判時，違規訊息會顯示指紋。把它記錄到 `.repo-guard-exceptions.json`，並寫明理由：

```json
{
  "exceptions": [
    { "path": "docs/example.md", "kind": "email", "line_sha256": "<指紋>", "reason": "說明為什麼是誤判" }
  ]
}
```

例外只對這個檔案的這一行有效，行內容一改就失效。白名單、作者與本機識別清單不能豁免。**真實機密不要記錄例外**，要視為已外洩並更換。

手動完成安裝時，在 repo 根目錄依序執行；前兩行每個 clone 都要做一次：

```text
git config user.email "<id>+<帳號>@users.noreply.github.com"
uv run tools/repo_guard.py --install-hook
uv run tools/dotfiles.py deploy
```

## 新增內容

要加入新的 skill，請見 [docs/adding-a-skill.md](docs/adding-a-skill.md)。新增其他路徑的檔案前，要先加進 `.repo-allowlist`，否則 commit 會被擋下。

## CI

每次 push 到任何分支，`.github/workflows/ci.yml` 都會執行以下工作，結果在 GitHub 的 Actions 頁面與各 job 的 summary：

| Job | 內容 |
|---|---|
| `unit-linux`、`unit-windows` | 全部單元測試；Windows 上兩種 PowerShell 都會跑入口腳本的測試。該跑的測試被略過時算失敗 |
| `guard` | 對完整歷史做入庫檢查，不比對本機識別清單 |
| `e2e-linux` | 在 Ubuntu、Fedora、Arch 與版本下限的容器內，實際跑完一行指令的流程 |
| `e2e-windows` | 在 Windows 上移除既有工具後跑同一套流程 |

E2E 的驅動腳本會真的安裝工具，`tests/e2e/windows.ps1` 還會解除安裝 Git，**不要在自己的電腦上執行**。

repo 公開後，標準 runner 不計費。`e2e-linux` 的 ubuntu 環境與 `e2e-windows-public` 只在 `main` 上另外用 README 的真實網址跑一次。

## 已知限制

- **解除不移除工具與 clone**：uv、git、Claude Code 可能已被其他專案使用，clone 內也可能有未推送的工作，所以只列出移除方式。
- **自動安裝 git 有範圍**：只支援 apt、dnf、pacman 與 winget，其他環境要先自行安裝 git。在進入設定階段前就失敗時，這次裝好的工具只列在當次訊息，解除時不會列出。
- **一行指令要信任來源**：它會直接執行從 `main` 下載的腳本，以及 uv 與 Claude Code 的官方安裝腳本。不放心時請先下載檢視。
- **檢查能被略過**：`git commit --no-verify` 會由 push 前的檢查補上；`git push --no-verify` 則只有 CI 能事後發現，無法阻止內容進入遠端。CI 沒有本機識別清單，姓名、主機名稱等個資只有本機檢查會比對。hook 也不會隨 clone 帶走，每個 clone 都要安裝一次。
- **Windows E2E 不等於新機器**：CI 的 Windows 機器已預裝許多工具，E2E 是移除既有工具後模擬乾淨環境，且 winget 改用 `wininet` 下載；runner 沒有 winget 時，自動安裝 git 會標為未驗證。
- **憑證規則有限**：內建規則只涵蓋常見格式，需要第二意見時可以再跑 `gitleaks git --no-banner --redact`。
- **`core.hooksPath`**：有設定時，要確認它會轉交給 `.git/hooks`，否則檢查不會執行。
- **模型差異**：Sonnet 的驗收全部通過。Haiku 曾用英文回覆英文提問，也較容易忽略 skill 的收尾步驟與「不加未確認規則」的指示。
- **未驗證的規則**：「提問使用 AskUserQuestion」無法用 `claude -p` 測試，只靠實際對話確認。
- **一個專案只有一種 Spec Kit 腳本**：Windows 導入的用 PowerShell，Linux 導入的用 bash。專案換到另一個作業系統時，需要對應的 shell。
- **最新版可能不相容**：`/sdd-init` 一律安裝最新穩定版，不同時間的新專案可能拿到不同版本。Spec Kit 改版造成不相容時，skill 會回報並停止。

## 開發規則

這個 repo 本身也用 SDD 開發。開發規則見 [constitution](.specify/memory/constitution.md)，功能規格見 [specs/](specs/)。

## 授權

Copyright 2026 flysangel。以 [Apache-2.0](LICENSE) 授權。Spec Kit 的檔案仍適用其 MIT 條款，範圍見 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
