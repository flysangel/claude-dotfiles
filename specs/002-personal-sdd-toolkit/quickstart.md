# Quickstart: 驗證個人化 SDD 工具組

**以下每一段都要在 Windows 與 Linux 各跑一次才算完成。** 指令介面見 [contracts/](contracts/)。

## 驗收環境

- **開發中**：不碰真實的 `~/.claude/`。部署一律加 `--target` 指向暫存目錄；驗收 skill 時，把 `home/skills/<skill>/` 複製到暫存測試專案的 `.claude/skills/`，並在該專案開新對話。
- **最終驗收**（T039、T040）：在維護者同意後才對真實的 `~/.claude/` 部署。CLAUDE.md 的實際行為與跨專案可用性只能在這一步確認。

## 前置條件

- 已安裝 `uv`、`git`、Claude Code
- 已 clone 此 repo，並在 repo 根目錄執行

## 1. 自動化測試

```text
uv run -m unittest discover -s tests
```

預期：全部通過，且真實的 `~/.claude/` 沒有變動。

## 2. 部署與還原（US1）

開發中的步驟都加上 `--target <暫存目錄>`，並略過第 3 步的跨專案確認。

1. 記下 `~/.claude/CLAUDE.md` 目前的內容。
2. 執行 `uv run tools/dotfiles.py deploy`，再執行一次。
   預期：第二次沒有產生新備份，`status` 回報 `clean`。
3. 執行 `/doctor prompt-audit`，確認沒有過時或衝突的內容。在另一個專案開新對話，確認 CLAUDE.md 寫明的預期行為成立，且 `/sdd-init`、`sdd-derive`、`sdd-grill` 可用。
4. 執行 `uv run tools/dotfiles.py undeploy`。
   預期：`CLAUDE.md` 與部署前完全相同，Orca 等未受管的 skill 不受影響。

## 3. 導入 Spec Kit（US2）

| 情境 | 操作 | 預期 |
|---|---|---|
| 空資料夾 | `/sdd-init` | 回報最新版本，`speckit-*` skill 可用，建議 `sdd-grill` |
| 有內容的專案 | `/sdd-init` | 既有檔案不變，建議 `sdd-derive` |
| 已導入的專案 | 修改 constitution 後再執行 `/sdd-init` | 沒有任何檔案改動 |
| 無法連線 | 中斷網路後執行 `/sdd-init` | 清楚說明原因，專案沒有新檔案 |

執行後用 `git status` 確認改動範圍，並確認 `.specify/scripts/` 符合該作業系統。

## 4. 導出（US3）

對 `tests/fixtures/sample-project/` 的副本依序執行 `/sdd-init` 與 `sdd-derive`，再依 `tests/skills/sdd-derive/scenarios.md` 驗收。

重點確認：

- 確認前沒有任何檔案被修改。
- 每條原則與每個功能都有依據或標為待確認。
- 假憑證沒有出現在任何產出中。
- 選兩個以上功能時，編號依相依順序，且 `feature.json` 指向第一份。
- 流程止於 spec。

## 5. 追問討論（US4）

用一句模糊的專案描述執行 `sdd-grill`，依 `tests/skills/sdd-grill/scenarios.md` 驗收。

重點確認：

- 一次一題，每題都有建議。
- 確認決策摘要前沒有寫入文件。
- 中斷後再次執行可接續；完成後進度檔已刪除，且進度檔從未進入 git。
- 產出沒有待釐清標記。

## 6. 觸發案例

```text
uv run tools/run_trigger_evals.py
```

預期：所有案例符合預期。此步驟會呼叫模型並產生費用，只在 skill 描述變更時執行。

## 7. 新增 skill（US5）

依 `docs/adding-a-skill.md` 加入範例 skill，用 `--target` 做一次修改與一次部署後，確認 skill 出現在目標目錄；刪除 `triggers.json` 時 `test_content.py` 應失敗。
