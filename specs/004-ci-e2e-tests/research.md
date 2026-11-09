# Research: 持續整合測試與 E2E 測試

查證日期：2026-11-07。runner 內容來自 `actions/runner-images` 的 README，計費來自 GitHub Docs。**workflow 尚未實際執行過；需要 push 才能驗證的項目都標在 quickstart。**

## 1. CI 平台

- **Decision**: GitHub Actions。
- **Rationale**: repo 已在 GitHub，結果直接顯示在 commit 與分支上，符合 SC-001；託管 runner 同時提供 Linux 與 Windows。
- **Alternatives**: 自架 runner 要維護機器；其他 CI 服務要另外授權與設定。

## 2. 單元測試的 job

- **Decision**:
  - `unit-linux`：在 `ubuntu-latest` 跑全部測試，另外以 runner 內建的 PowerShell 7 加上 `SETUP_PS1_TESTS=1` 跑 Windows 入口腳本的測試。
  - `unit-windows`：在 `windows-latest` 跑全部測試一次（使用 Windows PowerShell 5.1），再以 PowerShell 7 跑一次 `tests/test_setup_scripts_windows.py`。
- **網路測試**: `unit-linux` 設定 `RUN_NETWORK_TESTS=1`，讓 `/sdd-init` 的真實安裝每次都被驗證；只在 Linux 執行，避免增加 Windows 時間。
- **Rationale**: FR-002 要求兩種 PowerShell。只重跑入口腳本的測試，可以少花一次完整測試的 Windows 時間。測試目前以 `shutil.which("powershell") or "pwsh"` 選擇 PowerShell，所以要加上 `SETUP_PS1_SHELL` 環境變數來指定。
- **Alternatives**: 兩種 PowerShell 各跑完整測試，Windows 時間加倍；只跑 5.1 則漏掉 7。

## 3. 防止整組測試被略過

- **Decision**: 新增 `tests/gates.py`，提供 `requires(group, condition, reason)` 取代 `unittest.skipUnless`。環境變數 `REQUIRED_TEST_GROUPS` 列出的群組，條件不成立時改為測試失敗而不是略過。CI 的 Linux 設定 `setup-sh,powershell`，Windows 設定 `powershell`。
- **Rationale**: 003 的 Windows 測試在 Linux 上一直顯示略過，若 CI 的 Windows 環境因為找不到 PowerShell 而略過，結果仍會是通過（FR-004）。只在 CI 設定這個變數，本機執行的行為不變。
- **略過清單**: 以 `-v` 執行，日誌中每個略過的測試都有一行；workflow 另外把略過數寫進 job summary。
- **Alternatives**: 在 workflow 比對略過數量的固定值，每新增測試就要改 workflow。

## 4. 入庫檢查不需要本機識別清單的模式

- **Decision**: `repo_guard.py --history --without-identity`：執行除了識別清單以外的全部規則，輸出開頭說明這次沒有比對個人識別資訊，結束碼只依其餘規則決定。不加這個選項時行為不變。
- **Rationale**: 識別清單不能入庫，也不該放進 CI 的 secret，因為它的內容本身就是個資。目前沒有清單時 `--history` 直接回傳 3，CI 永遠不會通過（FR-015）。
- **Alternatives**: 把清單存成 secret，等於把個資交給第三方服務保管；讓 CI 忽略結束碼 3，會連真正無法完成的檢查也一起放過。
- **取捨**: 這會修改 001 的介面，要同步更新 `specs/001-repo-commit-guard/contracts/repo-guard.md`。

## 5. Linux E2E 環境

- **Decision**: `ubuntu-latest` 上以 matrix 跑四個容器，用 `docker run` 唯讀掛載 bare repo 與 `tests/e2e/`，不掛載 checkout：


| 環境 | 映像 | 使用者 | 準備 | 驗證重點 |
|---|---|---|---|---|
| ubuntu | `ubuntu:24.04` | 一般使用者加 sudo | 安裝 `curl`、`sudo` | apt 加 sudo，從零安裝 |
| fedora | `fedora:latest` | root | 無 | dnf |
| arch | `archlinux:latest` | root | 無 | pacman |
| minimum | `debian:10` | root | 從 archive 安裝 git 2.20，安裝 uv 0.4.0，放一個假的 `claude` | 版本下限、只有 `wget` |

- **Rationale**: 與 003 手動實測的組合相同，已知可行。用 `docker run` 而不是 job 的 `container:`，因為後者要在容器內執行 action，Arch 與舊版 Debian 不一定相容。
- **掛載**: 驅動腳本先把 bare repo 複製到容器內使用者的家目錄，否則擁有者不同時 git 會回報 dubious ownership（003 實測遇過）。結果行寫到標準輸出，由 workflow 轉寫到 `$GITHUB_STEP_SUMMARY`，容器不用處理 runner 的檔案權限。
- **來源**: 在 runner 上把 checkout 做成 bare repo，以 `CLAUDE_DOTFILES_REPO` 指向它，符合「使用這次 push 的內容」（FR-009），也不受 repo 私有影響。checkout 要取完整歷史，入庫檢查也需要。

## 6. Windows E2E 環境

- **Decision**: 在 `windows-latest` runner 上執行 `tests/e2e/windows.ps1`：
  1. **移除既有工具**：runner 預裝 Git 2.56（在 `C:\Program Files\Git`）。執行它的解除安裝程式 `unins000.exe /VERYSILENT /NORESTART`，並從 `PATH` 移除含有 `git.exe`、`uv.exe`、`claude.exe` 的目錄，確認三者都找不到後才開始。只改名不夠：Windows 的安裝紀錄還在，winget 可能判定 Git 已安裝而回傳非零結束碼。
  2. **winget**：runner-images 的 Windows Server 2025 README 沒有列出 winget。驅動先檢查；找不到時嘗試以 `Microsoft.WinGet.Client` 模組的 `Repair-WinGetPackageManager` 安裝。仍不可用時，不隱藏 git，並把「git 自動安裝」記為未驗證（FR-011）。
  3. 以 Windows PowerShell 5.1 執行入口腳本，因為使用者的一行指令就是在它裡面執行。
- **Rationale**: runner 以系統管理員身分執行，可以解除安裝；這是在不重灌系統的前提下最接近乾淨環境的做法。解除安裝必須在 bare repo 建好之後，job 之後的步驟也不能依賴 git；checkout 不保留憑證，收尾步驟不需要 git。
- **未知**: winget 能否在 runner 上安裝成功，要第一次執行才知道；兩種結果都有對應的處理。
- **Alternatives**: 只靠 `PATH` 過濾，會被 `setup.ps1` 的預設目錄檢查找到；只改名目錄，winget 仍看得到舊的安裝紀錄。

## 7. 用量估算

GitHub Free 每月含 USD 12 的運算額度；標準 runner 的費率是 Linux 每分鐘 USD 0.006、Windows USD 0.010；公開 repo 免費。（來源：GitHub Docs〈GitHub Actions billing〉）

| Job | 估計分鐘 | 費用（USD） |
|---|---|---|
| `unit-linux`（含網路測試） | 4 | 0.024 |
| `guard` | 1 | 0.006 |
| `e2e-linux` × 4 | 12 | 0.072 |
| `unit-windows` | 10 | 0.100 |
| `e2e-windows` | 8 | 0.080 |
| **合計** | 35 | **約 0.28** |

- 每月 USD 12 約可支撐 **40 次 push**。單元測試的分鐘數依 003 實測換算：Windows 完整測試約 166 秒，加上 runner 啟動與 uv 安裝。
- **風險**: 估算未經實測；Windows 佔大部分費用。超過時可以採用的做法依序是：只改 `specs/`、`*.md` 時略過 E2E；Windows E2E 只在 `main` 執行。這兩項都會改變「每次 push」的決定，要由維護者同意，因此寫在 README，不預先實作。
- **公開後**: 費用歸零，以上限制都不再需要。

## 8. 重複與取消

- **Decision**: `concurrency` 以分支為群組並設定 `cancel-in-progress: true`（FR-017）。
- **Rationale**: 同一分支連續 push 時只需要最新結果，也能節省額度。

## 9. 外部下載的暫時性失敗

- **Decision**: E2E 驅動在首次設定失敗、且輸出含有 `cannot download`、`apt-get failed`、`dnf failed`、`pacman failed` 或 `winget failed` 時，重試一次；兩次都失敗才算失敗，並在結果中標示是下載失敗（FR-013）。`setup.ps1` 的官方腳本失敗訊息要改成也含 `cannot download` 與網址，兩個系統才一致。
- **Rationale**: 官方安裝腳本與套件來源偶爾會短暫失敗，不應被當成程式錯誤；只重試一次，可以避免掩蓋真正的問題。

## 10. Action 的來源

- **Decision**: 只用 `actions/checkout` 與 `astral-sh/setup-uv`，並固定到 commit SHA，註解標示對應版本。workflow 的 `permissions` 設為 `contents: read`，checkout 一律設 `persist-credentials: false`。
- **Rationale**: 第三方 action 會在有 repo 存取權的環境中執行；固定 SHA 可以避免標籤被改指到其他內容。checkout 預設會把 token 寫進 `.git/config`，而 E2E 會執行下載來的安裝腳本，不保留憑證才不會讓它們讀到。uv 來自它自己的官方 action，與 003 使用的官方來源一致。

## 11. 公開後的真實網址

- **Decision**: 只在 repo 為公開且 push 到 `main` 時，`e2e-linux` 的 ubuntu 環境與 `e2e-windows` 各多跑一次 README 上的一行指令。
- **Rationale**: 真實網址指向 `main`，在其他分支執行等於測 `main` 而不是這次的改動。條件以 workflow 事件中的 repo 可見性判斷，公開時不需要改 workflow。

## 12. 本機驗證 workflow

- **Decision**: 以 `uv tool run check-jsonschema --builtin-schema vendor.github-workflows` 檢查 YAML；E2E 驅動先在本機的 podman 容器內實際執行。
- **Rationale**: workflow 的行為只能在 GitHub 上驗證，但語法錯誤與驅動腳本的錯誤可以先在本機抓到，減少試錯的 push。
