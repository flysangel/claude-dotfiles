# Implementation Plan: 授權聲明與一行指令設定

**Branch**: `003-license-oneline-setup` | **Date**: 2026-11-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-license-oneline-setup/spec.md`

## Summary

在根目錄加入 Apache-2.0 的 `LICENSE` 與涵蓋 Spec Kit 的 `THIRD_PARTY_NOTICES.md`。一行指令由 Linux 的 `tools/setup.sh` 與 Windows 的 `tools/setup.ps1` 接手：兩者只負責檢查作業系統、補齊工具與取得 repo，之後都交給跨平台的 `tools/machine_setup.py` 處理更新、開發設定、部署與解除。部署與 commit 防護沿用既有的 `tools/dotfiles.py` 與 `tools/repo_guard.py`。決策依據見 [research.md](research.md)。

## Technical Context

**Language/Version**: 入口腳本為 bash 與 Windows PowerShell 5.1；其餘為 Python 3.11+，只用標準庫，透過 `uv run` 執行

**Primary Dependencies**: `git`、`uv`、Claude Code（皆由入口腳本補齊）；`tools/dotfiles.py`、`tools/repo_guard.py`

**Storage**: 檔案。設定紀錄存在 repo 外的 `~/.config/claude-dotfiles/setup.json`，見 [data-model.md](data-model.md)

**Testing**: `unittest`（標準庫），在暫存目錄、隔離的 `HOME` 與假工具下執行。`setup.ps1` 的行為測試只在有 PowerShell 時執行

**Target Platform**: Linux（apt、dnf、pacman）與 Windows 10、11（winget）

**Project Type**: 命令列工具

**Performance Goals**: 網路正常時 10 分鐘內完成（SC-002）；重複執行不重新下載工具

**Constraints**: 不要求以系統管理員身分執行；入口腳本只用 ASCII；被 `iex` 執行時不得關閉使用者的視窗；輸出與入庫內容不得包含個人 email 與絕對路徑

**Scale/Scope**: 1 位維護者、數台機器；新增 3 支工具、2 份授權文件

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

設計完成後已重新檢查，結果相同。

| 原則 | 關卡問題 | 結果 | 說明 |
|---|---|---|---|
| I | 新增的入庫檔案都在白名單內，且不含機密與個資嗎？ | 通過 | `LICENSE` 與 `THIRD_PARTY_NOTICES.md` 要加入 `.repo-allowlist`；腳本在 `tools/**` 內。設定紀錄與提交身分只留在本機 |
| II | 每項客製化都說明了為何選擇該機制嗎？ | 通過 | 安裝是使用者主動執行的一次性操作，不需要常駐 context，因此用一般腳本，不用 hook、CLAUDE.md 或 skill |
| III | 指出需求來源了嗎？每個 CLAUDE.md 少於 200 行，且不含能從程式碼得知的內容嗎？ | 通過 | 來源：維護者明確要求補 LICENSE 與 Linux、Windows 一鍵設定。本功能不改動 CLAUDE.md |
| IV | 安裝可重複執行、可還原，且能在 Windows 與 Linux 上運作嗎？ | 有條件通過 | 重複執行與 `~/.claude/` 的還原都有測試。兩項差異記錄在 Complexity Tracking：解除時保留工具與 clone，入口腳本各依賴一種 shell |
| V | 每項產出都有驗證方式嗎？CLAUDE.md 規則具體可驗證且沒有矛盾嗎？ | 通過 | 單元測試加上 [quickstart.md](quickstart.md) 的乾淨環境驗收；`setup.ps1` 在這台 Linux 無法執行，要在 Windows 上驗收才算完成 |

## Project Structure

### Documentation (this feature)

```text
specs/003-license-oneline-setup/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── setup-cli.md
└── tasks.md             # 由 /speckit-tasks 產生
```

### Source Code (repository root)

```text
LICENSE                      # 新增：Apache-2.0 全文
THIRD_PARTY_NOTICES.md       # 新增：Spec Kit 的路徑、來源與 MIT 條款
README.md                    # 更新安裝與授權段落
.repo-allowlist              # 加入上述兩個新檔案

tools/
├── setup.sh                 # 新增：Linux 入口
├── setup.ps1                # 新增：Windows 入口
└── machine_setup.py         # 新增：更新 clone、開發設定、部署、解除

tests/
├── test_machine_setup.py    # 新增
├── test_setup_scripts.py    # 新增：以假工具驗證入口腳本
└── test_content.py          # 擴充：授權檔案與入口腳本的靜態檢查
```

**Structure Decision**: 入口腳本放在已列入白名單的 `tools/`，與其他工具放在一起。根目錄只放授權慣例要求的檔案，因為授權偵測工具與讀者都會在那裡尋找。

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 原則 IV「還原安裝前的狀態」：解除時保留自動安裝的工具與 clone | 安裝後 git、uv、Claude Code 可能已被其他專案依賴，clone 內也可能有未推送的工作；維護者已確認這個範圍（FR-020） | 自動移除可能破壞與這個 repo 無關的工作，也無法判斷使用者之後是否開始依賴；改為在摘要列出保留項目與移除方式 |
| 原則 IV「不得只依賴單一作業系統的 shell」：`setup.sh` 只能在 Linux 執行，`setup.ps1` 只能在 Windows 執行 | 全新機器上沒有跨平台的執行環境可以當入口，Python 也要等 uv 裝好才有 | 單一入口在全新機器上無法執行。改為把入口壓到最薄，其餘邏輯集中在跨平台的 Python，並讓兩個入口各對應一個系統 |
