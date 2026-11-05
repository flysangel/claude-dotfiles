# Implementation Plan: 公開 repo 入庫防護

**Branch**: `001-repo-commit-guard` | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-repo-commit-guard/spec.md`

## Summary

把 002 的 `tools/check_allowlist.py` 擴充並改名為 `tools/repo_guard.py`，補上 commit 訊息檢查、誤判例外、本機識別清單、完整歷史檢查、push 前檢查與啟用狀態查詢；另外新增 `tools/review_settings.py` 檢視 `~/.claude/settings.json`。完成後對此 repo 跑完整檢查，作為公開前的最終確認。決策依據見 [research.md](research.md)。

## Technical Context

**Language/Version**: Python 3.11+，只用標準庫，透過 `uv run` 執行

**Primary Dependencies**: `uv`、`git`

**Storage**: 檔案。`.repo-allowlist` 與 `.repo-guard-exceptions.json` 入庫；本機識別清單存在 repo 外

**Testing**: `unittest`（標準庫），全部在暫存 git repo 內進行

**Target Platform**: Windows 與 Linux 上的 git

**Project Type**: 命令列工具與 git hook

**Performance Goals**: 單次提交 50 個檔案以內，檢查增加不超過 2 秒（SC-003）。目前對 74 個已追蹤檔案的完整掃描約 0.17 秒

**Constraints**: 輸出不得包含機密完整值；檢查無法完成時視為不通過；不寫入 `core.hooksPath` 指向的共用目錄

**Scale/Scope**: 1 位維護者、數十個 commit、百餘個檔案

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

設計完成後已重新檢查，結果相同。

| 原則 | 關卡問題 | 結果 | 說明 |
|---|---|---|---|
| I | 新增的入庫檔案都在白名單內，且不含機密與個資嗎？ | 通過 | 這就是本功能的目的。新增的 `.repo-guard-exceptions.json` 要列入白名單；例外只存指紋與理由，不存機密原文；本機識別清單不入庫 |
| II | 每項客製化都說明了為何選擇該機制嗎？ | 通過 | 必須強制的檢查放 git hook，不放 CLAUDE.md；工具本身是一般腳本，不需要常駐 context |
| III | 指出需求來源了嗎？每個 CLAUDE.md 少於 200 行，且不含能從程式碼得知的內容嗎？ | 通過 | 來源：維護者明確要求公開前完成，且 Windows clone 需要 repo 可取得。本功能不改動 CLAUDE.md |
| IV | 安裝可重複執行、可還原，且能在 Windows 與 Linux 上運作嗎？ | 通過 | hook 可重複安裝與移除，邏輯都在 Python。hook 本身是 `sh` 腳本，由 git 執行，Git for Windows 內附 `sh`；Windows 上尚未實測，隨 002 的 T040 驗收 |
| V | 每項產出都有驗證方式嗎？CLAUDE.md 規則具體可驗證且沒有矛盾嗎？ | 通過 | 工具都有單元測試，涵蓋應阻止與應放行；另有真實 commit 的端對端測試與 [quickstart.md](quickstart.md) |

## Project Structure

### Documentation (this feature)

```text
specs/001-repo-commit-guard/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── repo-guard.md
│   └── review-settings.md
└── tasks.md             # 由 /speckit-tasks 產生
```

### Source Code (repository root)

```text
tools/
├── repo_guard.py            # 由 check_allowlist.py 改名並擴充
└── review_settings.py       # 新增：檢視 settings.json

tests/
├── test_repo_guard.py       # 由 test_check_allowlist.py 改名並擴充
└── test_review_settings.py

.repo-allowlist              # 沿用 002
.repo-guard-exceptions.json  # 新增：誤判例外，含範例專案的假憑證
```

**Structure Decision**: 擴充既有工具，不另建套件。檢查規則只有一份，`tests/test_content.py` 與完整檢查都重用它。

## Complexity Tracking

沒有需要說明的違規。
