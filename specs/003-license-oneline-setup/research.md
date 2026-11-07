# Research: 授權聲明與一行指令設定

驗證環境：Linux（2026-11-07）。官方安裝腳本與 Spec Kit 授權已實際下載確認。**這台機器沒有 PowerShell，Windows 相關內容來自官方文件與既有知識，尚未實測。**

## 1. 授權文件

- **Decision**: `LICENSE` 放未經改動的 Apache-2.0 全文（來源 `apache.org/licenses/LICENSE-2.0.txt`）。著作權人 `flysangel` 與年份寫在 README 的授權段落。不新增 `NOTICE`。
- **Rationale**: 全文不改動，授權偵測工具才能辨識；Apache-2.0 的全文本身不需要填入姓名。`NOTICE` 一旦存在，轉散布者就必須保留，這個 repo 沒有需要這樣要求的內容。
- **Alternatives**: 在 `LICENSE` 前加著作權行，違反 FR-001，也可能影響辨識。

## 2. Spec Kit 的第三方聲明

- **Decision**: 新增 `THIRD_PARTY_NOTICES.md`，列出 `.specify/`（不含 `.specify/memory/constitution.md`）與 `.claude/skills/speckit-*/`、上游網址、版本 1.2.6、完整 MIT 條款與 `Copyright GitHub, Inc.`。
- **Rationale**: MIT 要求散布時保留著作權與許可聲明。實際下載 `github/spec-kit` 的 v1.2.6 `LICENSE` 確認為 MIT。constitution 與 `specs/` 是這個 repo 自己寫的內容，適用 Apache-2.0。
- **Alternatives**: 把 MIT 全文放進每個目錄，檔案較多，`/sdd-init` 或 Spec Kit 更新時也容易被覆蓋。

## 3. 入口與邏輯的分工

- **Decision**: 入口腳本只做：檢查作業系統、檢查既有工具版本、安裝缺少的工具、確認或建立 clone、執行 `tools/machine_setup.py`。其餘都在 Python。
- **Rationale**: 全新機器上沒有 Python，入口只能是系統 shell，但同樣的邏輯寫兩份很難維持一致，也難以測試。uv 會自行取得符合 `requires-python` 的 Python，所以 Python 不必列為前置條件。
- **Alternatives**: 全部寫在兩支 shell 腳本，會有兩份更新與解除邏輯；打包成執行檔則多出建置與發布流程。

## 4. 工具安裝來源

| 工具 | Linux | Windows |
|---|---|---|
| uv | `https://astral.sh/uv/install.sh` | `https://astral.sh/uv/install.ps1` |
| Claude Code | `https://claude.ai/install.sh` | `https://claude.ai/install.ps1` |
| git | 系統的 `apt-get`、`dnf` 或 `pacman` | `winget install --id Git.Git` |

- **Rationale**: 都是官方或作業系統提供的來源，符合 FR-007。實際下載確認 uv 與 Claude Code 的安裝腳本都不需要系統管理員權限，Claude Code 腳本在 `sudo` 下還會拒絕執行，所以絕不能以 `sudo` 執行它。兩者的 Linux 腳本都同時支援 `curl` 與 `wget`。
- **權限**: 只有安裝 git 可能需要。Linux 上非 root 時用 `sudo`；`sudo` 不存在或被拒絕就停止並提示。Windows 上由 winget 觸發系統提示。
- **Alternatives**: 用 winget 或系統套件管理工具安裝 uv 與 Claude Code。官方文件指出 WinGet 版的 Claude Code 不會自動更新，版本也可能落後。

## 5. 被管線執行的陷阱

- **bash**: 全部內容包在函式內，最後一行才呼叫，下載中斷時不會執行半份腳本。子程序的 stdin 導向 `/dev/null`，否則它們會吃掉管線中尚未被讀取的腳本。
- **PowerShell 視窗**: 被 `iex` 執行時，`exit` 會關閉使用者的視窗。入口用 `throw` 回報失敗，互動視窗不會關閉，透過 `powershell -Command` 執行時結束碼非零。
- **第三方腳本的 `exit`**: Windows 上的官方安裝腳本可能呼叫 `exit`，因此在子程序 `powershell -NoProfile -ExecutionPolicy Bypass -Command` 內執行，以結束碼判斷結果。
- **編碼**: Windows PowerShell 5.1 對無 BOM 腳本的編碼判斷不可靠，兩支入口都限定 ASCII，訊息用英文，並有靜態測試。中文訊息只出現在 Python 層，沿用 `dotfiles.py` 重設輸出編碼的做法。
- **換行**: `.gitattributes` 把所有檔案定為 LF，bash 需要 LF，PowerShell 也能接受，不必另設規則。

## 6. 路徑更新

- **Decision**: 安裝工具後，把工具的預設安裝目錄（`~/.local/bin`，Windows 上另外重新讀取系統與使用者的 `Path`）加入目前程序的 `PATH`；仍找不到就停止並提示開新終端機。
- **Rationale**: 安裝程式只更新之後開啟的 shell，同一次執行還要繼續使用這些工具。

## 7. 既有工具的版本下限

- **Decision**: git 2.20、uv 0.4.0；Claude Code 不設下限。在安裝任何東西之前先全部檢查，版本過舊就停止，不自動升級。
- **Rationale**: 工具腳本依賴 uv 的 inline script metadata，以及一般的 git 指令。git 2.20 是足夠舊且仍容易取得的基準，實作時要跑測試確認。Claude Code 不參與設定流程，登入與更新由它自己處理。

## 8. Clone 的取得與更新

- **Decision**: 入口負責建立 clone，也在執行其中任何程式前確認既有目錄的 `origin` 符合預期；不符合就停止。更新由 `machine_setup.py` 處理：`git status --porcelain` 有內容或分支分岔就停止；可快轉就 `git merge --ff-only`，更新後重新執行自己一次，確保跑的是新版邏輯；本機領先或沒有 upstream 時不更新，繼續部署並提示。
- **Rationale**: 執行未確認目錄裡的程式等於執行任意程式碼，這項檢查不能放在被檢查的目錄內。其餘更新邏輯只需要一份。
- **預設位置**: `~/claude-dotfiles`，可用 `--dir` 或 `-Dir` 指定。

## 9. 設定紀錄的位置

- **Decision**: `~/.config/claude-dotfiles/setup.json`，與 001 的本機識別清單同一目錄。Linux 上權限設為 `600`。
- **Rationale**: 不能放在 `~/.claude/`，否則解除後無法與設定前逐檔相同（SC-004）；放在 clone 內則容易被清掉，也可能誤入庫。它可能含有設定前的 email，不能入庫。
- **取捨**: 入口在執行 Python 前失敗時，這次裝好的工具尚未寫入紀錄。失敗訊息會列出它們；重新執行時這些工具已存在，不會被列為自動安裝，解除摘要也就不會提到。影響只有少一行提示，不值得在兩支 shell 內各寫一份 JSON。

## 10. 開發設定的 email 檢查

- **Decision**: 只接受 `@users.noreply.github.com` 結尾的地址，比 `repo_guard.is_noreply` 嚴格；在任何部署或設定變更前檢查。
- **Rationale**: `is_noreply` 也接受 `noreply@` 開頭，那是為了 `Co-Authored-By` 這類情況，不適合當維護者的提交身分。FR-015 明確要求 GitHub noreply 格式。

## 11. 測試策略

- **Decision**: `machine_setup.py` 用暫存 git repo 與隔離的 `HOME` 測試。`setup.sh` 用 `PATH` 內的假工具與本機 bare repo 測試各情境，透過 `CLAUDE_DOTFILES_REPO` 改用本機來源。`setup.ps1` 只做靜態檢查（ASCII、無 `exit`），行為測試在有 `pwsh` 時才跑。
- **Rationale**: 測試不能碰使用者的 `~/.claude/`，也不能依賴 repo 已公開（FR-021）。真正裝工具的流程只能在乾淨環境驗收，見 [quickstart.md](quickstart.md)。

## 12. 信任模型

一行指令從 `main` 下載並立即執行，這是工具本身無法消除的風險：能修改 `main` 的人就能在使用者機器上執行程式。緩解方式是全程 HTTPS、入口腳本保持短小可讀、README 同時說明如何先下載再檢視，並且不要求以系統管理員身分執行。
