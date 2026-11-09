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

**Constraints**: CLAUDE.md < 200 行；skill 描述 ≤ 1,536 字元（Claude Code 的截斷上限）；不用 symlink；入庫內容不寫死絕對路徑

**Scale/Scope**: 1 位維護者、2 種作業系統、第一版 3 個 skill

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

設計完成後已重新檢查，結果相同。

| 原則 | 關卡問題 | 結果 | 說明 |
|---|---|---|---|
| I | 新增的入庫檔案都在白名單內，且不含機密與個資嗎？ | 通過 | 第一個 commit 就建立 `.repo-allowlist`、`tools/check_allowlist.py` 與 pre-commit hook，檢查內容與作者 email，見 [contracts/allowlist.md](contracts/allowlist.md)。hook 能被略過，也不會隨 clone 帶走，完整防護由 001 負責，**001 完成前此 repo 不得公開** |
| II | 每項客製化都說明了為何選擇該機制嗎？ | 通過 | 偏好放 CLAUDE.md；按需流程放 skill；導入與部署的確定性步驟放腳本；機器專屬內容放 `~/.claude/rules/`。原則 I 必須強制，因此用 git pre-commit hook；維護者已確認「不提交到 `main`」是偏好，因此不另加 hook |
| III | 指出需求來源了嗎？每個 CLAUDE.md 少於 200 行，且不含能從程式碼得知的內容嗎？ | 通過 | 需求來源見下方表格。行數由測試檢查，內容由 `/doctor prompt-audit` 與審閱檢查 |
| IV | 安裝可重複執行、可還原，且能在 Windows 與 Linux 上運作嗎？ | 有例外 | 部署與導入在同一環境重複執行結果相同，移除導入時，未修改的檔案會還原，已修改的檔案會保留並回報。「一律最新版」造成不同時間的結果不同，見 Complexity Tracking |
| V | 每項產出都有驗證方式嗎？CLAUDE.md 規則具體可驗證且沒有矛盾嗎？ | 通過 | 腳本有單元測試，skill 有觸發案例與情境驗收，CLAUDE.md 規則附預期行為並由 `/doctor prompt-audit` 檢查矛盾，部署與導入流程見 [quickstart.md](quickstart.md) |

**需求來源（原則 III）**

| 產出 | 來源 |
|---|---|
| CLAUDE.md | 維護者明確要求：互動式提問、每次異動後在分支上 commit；繁中回覆與 SDD 工作方式由維護者確認 |
| 部署 | 維護者明確要求：設定要用於多台機器，支援 Windows 與 Linux |
| `sdd-init` | 維護者明確要求：以後新專案都能快速使用 Spec Kit |
| `sdd-grill` | 維護者明確要求；實際遇到：此 repo 的 constitution 與 spec 都靠人工追問才定案 |
| `sdd-derive` | 維護者明確要求：從既有專案導出 constitution 與 spec |

## Project Structure

### Documentation (this feature)

```text
specs/002-personal-sdd-toolkit/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── allowlist.md
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
├── check_allowlist.py       # 最小白名單與 commit 前檢查
├── dotfiles.py              # deploy / undeploy / status
└── run_trigger_evals.py     # 用 claude -p 執行觸發案例，手動執行

tests/
├── test_check_allowlist.py
├── test_dotfiles.py
├── test_trigger_evals.py
├── test_sdd_init.py
├── test_content.py          # CLAUDE.md 行數、skill 格式、絕對路徑等靜態檢查
├── skills/<skill>/
│   ├── triggers.json        # 應觸發與不應觸發的提示
│   └── scenarios.md         # 行為驗收情境
└── fixtures/sample-project/ # 含假憑證與文件矛盾的範例專案

docs/adding-a-skill.md       # FR-029
.gitattributes               # 入庫文字檔一律使用 LF
.repo-allowlist              # 可入庫路徑的白名單
README.md                    # 使用手冊
```

**Structure Decision**: `sdd-init` 做成只能手動執行的 skill，因為導入要能在任何專案用一個步驟完成；全域命令需要各系統設定 PATH，放在 repo 內則每次都要指定路徑。部署內容放在 `home/`，不放在此 repo 的 `.claude/`。這樣開發中的版本不會在此 repo 內被載入，也不會和 Spec Kit 的 skill 混在一起。

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| IV：不同時間導入可能得到不同版本的 Spec Kit | 維護者明確選擇新專案一律用最新版 | 固定版本可完全重現，但維護者已選擇不採用。以回報版本、同專案不自動升級、相依缺失時明確停止來降低風險 |
| IV：移除導入時，已修改的檔案與 `.git` 預設不還原 | 這些內容屬於維護者，例如已填寫的 constitution 與 commit 歷史 | 直接還原會刪掉維護者的內容；已修改的檔案改為保留並回報，要移除時再明確加 `--all`；`.git` 一律保留 |

## `sdd-derive` 首次實際使用（2026-11-09）

在一個既有的基礎設施專案上使用，維護者已決定封存該專案並重新設計。

| 項目 | 結果 |
|---|---|
| 未導入 Spec Kit | 前置檢查停止，提示先執行 `/sdd-init`，沒有寫入 |
| 草稿 | 只讀取，提出 15 條附依據的原則與功能清單，並列出文件矛盾 |
| 確認前 | 沒有修改專案檔案 |
| 產生 spec | 維護者選定 14 項功能，各呼叫一次 `speckit-specify`，依相依順序編號 |
| 收尾 | `feature.json` 指回第一份，列出清單，沒有進入 plan |

**結論**：skill 有實際價值，保留。

**SC-005 無法量測**：維護者決定重新設計，不採用導出的 constitution，所以沒有「被改寫或刪除的原則比例」可算。

**發現的落差**：維護者只要 spec、不要 constitution 時，skill 沒有對應路徑，第一次在該決定後直接停止，要再追問一次才匯出。
