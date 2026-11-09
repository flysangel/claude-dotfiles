# Implementation Plan: 持續整合測試與 E2E 測試

**Branch**: `004-ci-e2e-tests` | **Date**: 2026-11-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-ci-e2e-tests/spec.md`

## Summary

新增一個 GitHub Actions workflow，每次 push 執行四類工作：Linux 與 Windows 的單元測試、伺服器端的入庫檢查、Linux 四個容器環境的 E2E，以及 Windows 的 E2E。E2E 的流程寫成兩支驅動腳本（bash 與 PowerShell），依序跑完 003 quickstart 的情境並逐階段回報。另外補上兩個小改動：測試可以宣告「在這個系統上必須執行」，避免整組被略過卻顯示通過；`repo_guard.py --history` 加上不需本機識別清單的模式。決策依據見 [research.md](research.md)。

## Technical Context

**Language/Version**: GitHub Actions workflow（YAML）；E2E 驅動為 bash 與 Windows PowerShell 5.1；測試與工具維持 Python 3.11+ 標準庫

**Primary Dependencies**: GitHub 託管的 `ubuntu-latest` 與 `windows-latest` runner；`actions/checkout`；`astral-sh/setup-uv`；runner 內建的 docker 與 PowerShell 7

**Storage**: 無。結果寫在 workflow 日誌與 job summary

**Testing**: 既有的 `unittest`；workflow 本身用 GitHub workflow schema 檢查，並以故意失敗的 push 驗證（見 [quickstart.md](quickstart.md)）

**Target Platform**: GitHub Actions；E2E 環境為 Ubuntu 24.04、Fedora、Arch、Debian 10（版本下限）容器，以及 Windows Server 2025 runner

**Project Type**: CI 設定與測試腳本

**Performance Goals**: 每次 push 20 分鐘內完成（SC-002）；估計每次約 USD 0.28，見 research 第 7 節

**Constraints**: 不使用任何 secret，checkout 不保留存取權杖；輸出不得含真實 email；repo 為私有時不能依賴公開網址；只使用 `actions/*` 與 `astral-sh/setup-uv` 兩個來源的 action，並固定到 commit

**Scale/Scope**: 1 個 workflow、8 個 job（含 matrix）、2 支 E2E 驅動腳本

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

設計完成後已重新檢查，結果相同。

| 原則 | 關卡問題 | 結果 | 說明 |
|---|---|---|---|
| I | 新增的入庫檔案都在白名單內，且不含機密與個資嗎？ | 通過 | `.github/**` 要加入 `.repo-allowlist`。workflow 不使用 secret，E2E 用假的 noreply 地址；伺服器端入庫檢查是原則 I 的額外防線 |
| II | 每項客製化都說明了為何選擇該機制嗎？ | 通過 | 本機 hook 能被 `--no-verify` 略過，伺服器端檢查只能放在 CI；測試在 CI 執行，不涉及 CLAUDE.md、skill 或 subagent |
| III | 指出需求來源了嗎？每個 CLAUDE.md 少於 200 行，且不含能從程式碼得知的內容嗎？ | 通過 | 來源：維護者要求測試與 E2E，以及 003 在 Windows 手動才發現的失敗。本功能不改動 CLAUDE.md |
| IV | 安裝可重複執行、可還原，且能在 Windows 與 Linux 上運作嗎？ | 通過 | 本功能就是讓兩個系統的安裝每次 push 都被驗證；E2E 也涵蓋重跑與解除 |
| V | 每項產出都有驗證方式嗎？CLAUDE.md 規則具體可驗證且沒有矛盾嗎？ | 通過 | workflow 以 schema 檢查與故意失敗的 push 驗證；測試閘門與 `--without-identity` 有單元測試 |

## Project Structure

### Documentation (this feature)

```text
specs/004-ci-e2e-tests/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── ci-workflow.md
│   ├── e2e-driver.md
│   └── test-gates.md
└── tasks.md             # 由 /speckit-tasks 產生
```

### Source Code (repository root)

```text
.github/workflows/
└── ci.yml                       # 新增：單元測試、入庫檢查、E2E

tests/
├── ci_summary.sh                # 新增：把測試結果寫進 job summary
├── gates.py                     # 新增：宣告必須執行的測試群組
├── test_ci_workflow.py          # 新增：workflow 的靜態檢查
├── test_gates.py                # 新增
├── test_setup_scripts.py        # 改用 gates
├── test_setup_scripts_windows.py  # 改用 gates，並可指定 PowerShell 版本
├── test_repo_guard.py           # 擴充：--without-identity
└── e2e/
    ├── prepare.sh               # 新增：容器的環境準備
    ├── linux.sh                 # 新增：容器內的 E2E 驅動
    └── windows.ps1              # 新增：Windows runner 的 E2E 驅動

tools/
└── repo_guard.py                # 擴充：--history --without-identity

.repo-allowlist                  # 加入 .github/**
README.md                        # CI 說明、已知限制與 Windows 驗收狀態
```

**Structure Decision**: E2E 驅動放在 `tests/e2e/`，與單元測試分開，因為它們會真的下載並安裝工具，只該在拋棄式環境執行。workflow 只負責準備環境與呼叫驅動，情境邏輯都在驅動腳本內，必要時也能在本機容器重現。

## Complexity Tracking

無違反憲章原則的項目。
