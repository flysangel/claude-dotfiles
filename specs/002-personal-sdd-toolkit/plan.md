# Implementation Plan: 個人化 SDD 工具組

**Branch**: `002-personal-sdd-toolkit` | **Date**: 2026-11-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-personal-sdd-toolkit/spec.md`

## Summary

此 repo 管理一份個人化 CLAUDE.md 與三個 skill：`sdd-init`（導入 Spec Kit）、`sdd-derive`（從既有專案導出）、
`sdd-grill`（追問討論）。一個跨平台的 Python 指令把它們複製到 `~/.claude/`，並負責備份與還原。
`sdd-derive` 與 `sdd-grill` 只做到決策確認，文件交由 Spec Kit 自己的 `speckit-constitution`、
`speckit-specify` 產生。決策依據見 [research.md](research.md)。

## Technical Context

**Language/Version**: Python 3.11+，只用標準庫，透過 `uv run` 執行；skill 本體為 Markdown

**Primary Dependencies**: `uv`、`git`、Spec Kit（導入時由 `uv tool run` 取得最新穩定版）

**Storage**: 檔案。部署紀錄與備份存在 `~/.claude/.dotfiles/`，不入庫；導入紀錄存在目標專案的 `.specify/sdd-init.json`

**Testing**: `unittest`（標準庫）；skill 另有觸發案例與情境驗收

**Target Platform**: Windows 與 Linux 上的 Claude Code

**Project Type**: 個人設定套件加命令列工具

**Performance Goals**: 部署 5 分鐘內完成並確認（SC-001）；導入 2 分鐘內完成（SC-003）

**Constraints**: CLAUDE.md ≤ 200 行；skill 描述 ≤ 1,536 字元（Claude Code 的截斷上限）；不用 symlink；入庫內容不寫死絕對路徑

**Scale/Scope**: 1 位維護者、2 種作業系統、第一版 3 個 skill

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

設計完成後已重新檢查，結果相同。

| 原則 | 關卡問題 | 結果 | 說明 |
|---|---|---|---|
| I | 新增的入庫檔案都在白名單內，且不含機密與個資嗎？ | 有條件通過 | 內容不含機密與個資，測試資料只用假值與保留網域。但白名單由 001 實作，**001 完成前此 repo 不得公開**；新增路徑見 Project Structure，需列入 001 的初始白名單 |
| II | 每項客製化都說明了為何選擇該機制嗎？ | 通過 | 偏好放 CLAUDE.md；按需流程放 skill；導入與部署的確定性步驟放腳本；機器專屬內容放 `~/.claude/rules/`。本功能沒有必須強制的規則，因此不新增 hook |
| III | 指出實際需求了嗎？常駐內容仍在上限內嗎？ | 有例外 | CLAUDE.md 上限由測試檢查。`sdd-derive` 尚無重複發生的紀錄，見 Complexity Tracking |
| IV | 安裝可重複執行、可還原，且能在 Windows 與 Linux 上運作嗎？ | 有例外 | 部署與導入在同一環境重複執行結果相同，且可還原。「一律最新版」造成不同時間的結果不同，見 Complexity Tracking |
| V | 每項產出都有驗證方式嗎？ | 通過 | 腳本有單元測試，skill 有觸發案例與情境驗收，CLAUDE.md 規則附預期行為，部署與導入流程見 [quickstart.md](quickstart.md) |

## Project Structure

### Documentation (this feature)

```text
specs/002-personal-sdd-toolkit/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── dotfiles-cli.md
│   ├── sdd-init.md
│   └── skills.md
└── tasks.md             # 由 /speckit-tasks 產生
```

### Source Code (repository root)

```text
home/                        # 鏡像 ~/.claude/，是部署內容的唯一來源
├── CLAUDE.md
└── skills/
    ├── sdd-init/
    │   ├── SKILL.md
    │   └── scripts/sdd_init.py
    ├── sdd-derive/SKILL.md
    └── sdd-grill/SKILL.md

tools/
├── dotfiles.py              # deploy / undeploy / status
└── run_trigger_evals.py     # 用 claude -p 執行觸發案例，手動執行

tests/
├── test_dotfiles.py
├── test_sdd_init.py
├── test_content.py          # CLAUDE.md 行數、skill 格式、絕對路徑等靜態檢查
├── skills/<skill>/
│   ├── triggers.json        # 應觸發與不應觸發的提示
│   └── scenarios.md         # 行為驗收情境
└── fixtures/sample-project/ # 含假憑證與文件矛盾的範例專案

docs/adding-a-skill.md       # FR-029
.gitattributes               # 入庫文字檔一律使用 LF
```

**Structure Decision**: 部署內容放在 `home/`，不放在此 repo 的 `.claude/`。這樣開發中的版本不會在此 repo 內被載入，也不會和 Spec Kit 的 skill 混在一起。

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| IV：不同時間導入可能得到不同版本的 Spec Kit | 維護者明確選擇新專案一律用最新版 | 固定版本可完全重現，但維護者已選擇不採用。以回報版本、同專案不自動升級、相依缺失時明確停止來降低風險 |
| III：`sdd-derive` 尚無重複發生的紀錄 | 維護者明確提出要將既有專案轉為 SDD | 延後會少掉主要需求；第一次實際使用即作為驗證，若未被使用再移除 |
| 規格明列兩個 skill，實作多一個 `sdd-init` | 導入要能在任何專案用一個步驟完成，又不想依賴 PATH 或 repo 路徑 | 全域命令需要各系統額外設定 PATH；放在 repo 內則每次都要指定路徑 |
