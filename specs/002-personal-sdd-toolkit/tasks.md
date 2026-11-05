---

description: "Task list for the personal SDD toolkit"
---

# Tasks: 個人化 SDD 工具組

**Input**: Design documents from `specs/002-personal-sdd-toolkit/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: 包含測試任務。憲章原則 V 要求每項產出都有驗證方式，spec FR-027 也要求 skill 有觸發案例。

**Organization**: 依 user story 分組，每個 story 都能獨立實作與驗證。

**Commit**: 每完成一項異動就在目前分支 commit，不直接提交到 `main`，也不 push。T001 到 T003 合成第一個 commit；之後由 pre-commit hook 檢查，不得用 `--no-verify` 略過。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可以平行進行（不同檔案，且不依賴未完成的任務）
- **[Story]**: 所屬的 user story（US1 到 US5）

## Path Conventions

路徑相對於 repo 根目錄，結構見 `plan.md`。部署內容一律放在 `home/`。

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 先建立憲章原則 I 要求的白名單與檢查，再建立 repo 基本設定

- [X] T001 建立 `.repo-allowlist`，內容依 `specs/002-personal-sdd-toolkit/contracts/allowlist.md`
- [X] T002 建立 `tests/test_check_allowlist.py`，涵蓋：白名單外的檔案不通過、白名單內的檔案通過、刪除的檔案不檢查、個人家目錄路徑與全域 git email 不通過、noreply 與保留網域的 email 通過、假憑證樣本不通過、`tests/fixtures/sample-project/` 的假憑證通過、白名單遺失回傳 3、輸出不含機密完整值、作者或提交者不是 noreply 時不通過、`--install-hook` 重複執行結果相同且不覆蓋其他 hook、`--uninstall-hook` 只移除自己安裝的 hook；全部在暫存 git repo 內進行，違規樣本在執行時組合
- [X] T003 依 `contracts/allowlist.md` 建立 `tools/check_allowlist.py`，用 PEP 723 宣告版本需求，只用標準庫；完成後執行 `--all` 確認目前所有已追蹤檔案都通過，再用 `--install-hook` 安裝到此 repo，確認此 repo 的 `user.email` 是 noreply 地址
- [X] T004 [P] 建立 `.gitattributes`，內容為 `* text=auto eol=lf`，讓 Windows 與 Linux 上的檔案雜湊值一致
- [X] T005 [P] 建立 `.gitignore`，排除 `__pycache__/`、`*.pyc`；不得排除白名單列出的路徑
- [X] T006 確認 `specs/002-personal-sdd-toolkit/quickstart.md` 第 1 段的測試指令可在此 repo 執行，不可行就改成可用的 `uv run` 指令並同步修正該檔

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 所有 story 共用的靜態檢查與 skill 驗收工具

**⚠️ CRITICAL**: 完成前不要開始任何 user story

- [X] T007 建立 `tests/test_content.py`，檢查 `home/CLAUDE.md`（存在時）少於 200 行、含 markdown 標題與條列；每個 `home/skills/*/SKILL.md` 都有 `name` 與 `description`，且 `description` 加 `when_to_use` 不超過 1,536 字元；每個 skill 都有 `tests/skills/<skill>/triggers.json` 與 `scenarios.md`；`home/` 內不得出現個人家目錄絕對路徑或非保留網域的 email，這項規則重用 `tools/check_allowlist.py`
- [X] T008 建立 `tools/run_trigger_evals.py`，讀取 `tests/skills/*/triggers.json` 的 `should_trigger`、`should_not_trigger`，以 `claude -p` 執行並判斷 skill 是否被呼叫；支援指定單一 skill，執行前先提示會產生費用。先確認 `claude -p` 的輸出能可靠判斷；不可靠時改為輸出手動驗收清單，並更新 `specs/002-personal-sdd-toolkit/research.md` 第 10 節

**Checkpoint**: 靜態檢查可執行，user story 可以開始

---

## Phase 3: User Story 1 - 在任何機器上部署個人化設定 (Priority: P1) 🎯 MVP

**Goal**: 一個指令就能部署 CLAUDE.md 與 skill，會先備份，也能完整還原

**Independent Test**: 在已有 CLAUDE.md 的暫存目標部署，確認內容與備份正確；解除部署後逐位元組比對，應與部署前相同

### Tests for User Story 1

- [X] T009 [US1] 建立 `tests/test_dotfiles.py`，全部使用暫存目錄與 `--target`，涵蓋：首次部署、已有 CLAUDE.md 時先備份、重複部署不產生新備份、解除部署後逐位元組相同（SC-002）、未受管的 skill 與 `rules/` 不受影響、同名未受管 skill 回傳結束碼 2、`--force` 備份後取代、本機修改後覆蓋前另存備份、中斷後（紀錄為 `in_progress`）可重新部署或解除部署、repo 已刪除的受管檔案會被移除，以及 `status` 的 `not-deployed`、`clean`、`local-modified`、`repo-ahead`、`incomplete` 與判斷優先順序，以及沒有部署紀錄時 `undeploy` 不改動

### Implementation for User Story 1

- [X] T010 [US1] 在 `tools/dotfiles.py` 實作部署紀錄的讀寫：位置 `<target>/.dotfiles/manifest.json`，欄位 `status`（`in_progress` 或 `complete`）、`repo_commit`、`entries[]`（`path` 使用 `/` 分隔、`sha256`、`original` 為 `absent` 或備份相對路徑與雜湊值）；寫入須為原子操作；PEP 723 宣告 `requires-python >= 3.11`，只用標準庫
- [X] T011 [US1] 在 `tools/dotfiles.py` 實作 `deploy`：複製 `home/` 到目標，開始前先寫入 `in_progress`；再次部署時 `original` 維持第一次的值；依 `contracts/dotfiles-cli.md` 處理衝突、結束碼與完成提示；備份放在 `<target>/.dotfiles/backups/`；不使用 symlink
- [X] T012 [US1] 在 `tools/dotfiles.py` 實作 `undeploy`：依 `original` 還原或刪除、移除空目錄與部署紀錄；本機已修改的檔案先另存備份；只處理紀錄中的檔案；沒有部署紀錄時不改動並回報
- [X] T013 [US1] 在 `tools/dotfiles.py` 實作 `status`，只讀取，依 contract 的順序判斷五種狀態並列出差異檔案；輸出不得包含被備份檔案的內容
- [X] T014 [US1] 建立 `home/CLAUDE.md`，少於 200 行，用標題與條列分組，每條規則具體且附可觀察的預期行為，內容為：以繁體中文回覆；提問使用互動式選項；每次異動後在分支上 commit，不提交到 `main`，不自動 push；以 SDD 與 Spec Kit 為主要工作方式，說明何時使用 `/sdd-init`、`sdd-derive`、`sdd-grill`。不得放機密、個資或機器專屬內容，也不得放能從程式碼得知的內容
- [X] T015 [US1] 依 `specs/002-personal-sdd-toolkit/quickstart.md` 第 2 段，先用 `--target` 對暫存目錄驗收，`/doctor prompt-audit` 在非互動模式超過 $0.50 預算而沒有結果，改在 T039 互動式執行

**Checkpoint**: 部署與還原可獨立運作

---

## Phase 4: User Story 2 - 新專案快速導入 Spec Kit (Priority: P1)

**Goal**: 一個步驟導入最新版 Spec Kit，不覆蓋既有內容，並提示下一步

**Independent Test**: 在空資料夾與有內容的資料夾分別導入，確認 Spec Kit 可用、既有檔案不變、重複執行不改動

### Tests for User Story 2

- [X] T016 [P] [US2] 建立 `tests/test_sdd_init.py`，以假的初始化函式取代網路呼叫，涵蓋：只複製不存在的檔案、已導入時不改動、失敗時移除這次建立的檔案、缺少工具與無法取得版本時回傳 3、Windows 選 `ps` 與 Linux 選 `sh`、穩定版標籤選擇會排除預發布版、下一步建議（有內容為 `sdd-derive`，空專案為 `sdd-grill`）、`remove` 只刪除未修改的檔案（包含未修改的 `constitution.md` 範本）、已修改的檔案保留並回報、`--all` 才一併移除、不碰 `specs/` 與 `.git`、沒有紀錄檔時回傳 1 且不改動；不在 git repo 內時導入成功才執行 `git init` 且不 commit、失敗時不建立 `.git`、已在上層 repo 內時不執行
- [X] T017 [US2] 在 `tests/test_sdd_init.py` 加入需設定環境變數 `RUN_NETWORK_TESTS=1` 才執行的真實導入測試，確認最新版可安裝、`speckit-*` skill 存在，且產生的檔案不包含暫存目錄路徑（research 第 5 節待確認項目）

### Implementation for User Story 2

- [X] T018 [US2] 在 `home/skills/sdd-init/scripts/sdd_init.py` 實作 `init`，依 `contracts/sdd-init.md` 的七個步驟：用 `git ls-remote --tags` 取最高穩定版，以 `uv tool run --from git+https://github.com/github/spec-kit.git@<tag> specify init <temp> --integration claude --script <sh|ps> --ignore-agent-tools --non-interactive` 初始化到暫存目錄，再複製缺少的檔案；最後一步在目標不屬於任何 git repo 時執行 `git init`，不 commit（FR-033）；PEP 723 宣告版本需求，只用標準庫
- [X] T019 [US2] 在同一腳本寫入 `.specify/sdd-init.json`，欄位 `speckit_version`、`script`（`sh` 或 `ps`）、`created[]`（相對路徑與雜湊值）、`skipped[]`；完成時回報版本、建立數、略過的檔案、下一步，並提示專案換到另一個作業系統需要對應的 shell（FR-008）
- [X] T020 [US2] 在同一腳本實作 `remove`，依 `.specify/sdd-init.json` 刪除雜湊值相符的檔案，包含未修改的 `constitution.md` 範本，並移除紀錄檔與空目錄；已修改的檔案保留並回報，`--all` 才一併移除；一律不動 `specs/` 與 `.git`；沒有紀錄檔時不改動並回傳 1
- [X] T021 [US2] 建立 `home/skills/sdd-init/SKILL.md`，設定 `disable-model-invocation: true`，用 `${CLAUDE_SKILL_DIR}` 呼叫腳本並轉述結果
- [X] T022 [P] [US2] 建立 `tests/skills/sdd-init/triggers.json`（確認不會自動觸發）與 `tests/skills/sdd-init/scenarios.md`（對應 spec US2 的五個驗收情境）
- [X] T023 [US2] 依 `specs/002-personal-sdd-toolkit/quickstart.md` 第 3 段驗收四個情境；依該檔「驗收環境」把 skill 複製到暫存測試專案

**Checkpoint**: 導入可獨立運作

---

## Phase 5: User Story 3 - 從既有專案導出 constitution 與 spec (Priority: P2)

**Goal**: 從既有專案提出有依據的草稿與功能清單，確認後依相依順序產生文件

**Independent Test**: 對範例專案執行，確認每項都有依據、確認前沒有改動任何檔案、假憑證沒有出現在產出中

**依賴**: 驗收需要 US2 的導入，撰寫不受影響

### Tests for User Story 3

- [ ] T024 [P] [US3] 建立 `tests/fixtures/sample-project/`，至少含兩個有相依關係的功能、一處文件與程式碼矛盾、一個相依套件目錄、一個明顯為假的憑證（只用假值與保留網域）
- [ ] T025 [P] [US3] 建立 `tests/skills/sdd-derive/triggers.json`（應觸發與不應觸發，依 `contracts/skills.md`）與 `tests/skills/sdd-derive/scenarios.md`（對應 spec US3 的八個驗收情境與相關 edge cases）

### Implementation for User Story 3

- [ ] T026 [US3] 建立 `home/skills/sdd-derive/SKILL.md`，依 `contracts/skills.md` 寫入前置檢查與五個步驟；每條原則標明類型（`已經這樣做`、`應該這樣做`）、依據與狀態（`有依據`、`待確認`）；`應該這樣做` 須維護者確認；不把機密值帶入對話或產出；處理內容不足、文件矛盾、大型專案、已有 constitution 的情況；文件語言依 FR-030
- [ ] T027 [US3] 在 `home/skills/sdd-derive/SKILL.md` 寫入「多份 spec 的接續」：依相依順序呼叫 `speckit-specify`，完成後將 `.specify/feature.json` 的 `feature_directory` 指向第一份；檔案不存在或沒有該欄位時只回報、不寫入；列出清單、相依關係與切換方式後停止，不進入 plan
- [ ] T028 [US3] 依 `specs/002-personal-sdd-toolkit/quickstart.md` 第 4 段驗收，依「驗收環境」把 skill 複製到範例專案副本，並確認 skill 能實際呼叫 `speckit-constitution` 與 `speckit-specify`（research 第 7 節待確認項目）；不可行時回報維護者，並更新 `research.md` 與 `contracts/skills.md`

**Checkpoint**: 導出可獨立運作

---

## Phase 6: User Story 4 - 透過追問討論出 constitution 與 spec (Priority: P2)

**Goal**: 逐題追問到每個功能都有結論，確認後產生文件，中斷後可接續

**Independent Test**: 用一句模糊的描述開始討論，確認一次一題且有建議、中斷後可接續、產出沒有待釐清標記

**依賴**: 驗收需要 US2 的導入；共用 T028 對 skill 互相呼叫的確認結果

### Tests for User Story 4

- [ ] T029 [P] [US4] 建立 `tests/skills/sdd-grill/triggers.json`（依 `contracts/skills.md`）與 `tests/skills/sdd-grill/scenarios.md`（對應 spec US4 的九個驗收情境與相關 edge cases）

### Implementation for User Story 4

- [ ] T030 [US4] 建立 `home/skills/sdd-grill/SKILL.md`，依 `contracts/skills.md` 寫入前置檢查與規則：一次一題並附建議與理由、能查到的自行查閱、追問含糊回答、指出矛盾、涵蓋每個功能、技術選型記為留給 plan、文件語言依 FR-030
- [ ] T031 [US4] 在 `home/skills/sdd-grill/SKILL.md` 寫入進度規則：每個決定後更新 `.specify/sdd-grill-progress.md`，建立時加入 `.specify/.gitignore`，不記錄機密值；進度檔存在時列出已決定事項，由維護者選擇接續或重新開始，專案有變更時先提示；文件寫入成功後或重新開始時刪除
- [ ] T032 [US4] 在 `home/skills/sdd-grill/SKILL.md` 寫入收尾：維護者確認決策摘要後呼叫 `speckit-constitution`，再依相依順序為每個功能呼叫一次 `speckit-specify`；接續規則與 T027 相同；中途停止時提供摘要，不寫入 constitution 或 spec
- [ ] T033 [US4] 依 `specs/002-personal-sdd-toolkit/quickstart.md` 第 5 段驗收，依「驗收環境」把 skill 複製到暫存測試專案

**Checkpoint**: 追問討論可獨立運作

---

## Phase 7: User Story 5 - 逐項加入新的常用 skill (Priority: P3)

**Goal**: 有實際需求時，能用一次修改與一次部署加入新 skill

**Independent Test**: 依文件加入範例 skill，部署後可用，解除部署後移除

### Implementation for User Story 5

- [ ] T034 [US5] 建立 `docs/adding-a-skill.md`，說明加入 skill 的步驟：指出需求來源（實際遇到的需求或維護者的明確要求）、放到 `home/skills/<name>/`、新增 `tests/skills/<name>/` 的兩個檔案、執行測試與觸發案例、重新部署
- [ ] T035 [US5] 在 `tests/test_content.py` 加入以暫存結構驗證的測試：缺少 `triggers.json` 時檢查不通過
- [ ] T036 [US5] 依 `specs/002-personal-sdd-toolkit/quickstart.md` 第 7 段驗收，全程使用 `--target`，完成後移除範例 skill

**Checkpoint**: 所有 user story 都可獨立運作

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 跨 story 的收尾與完整驗收

- [ ] T037 [P] 更新 `specs/001-repo-commit-guard/spec.md` 的 FR-010，改為沿用 `.repo-allowlist` 作為初始白名單，並以 001 的防護取代 `tools/check_allowlist.py` 與其 hook；註明 `tests/fixtures/sample-project/` 的假憑證需要誤判例外
- [ ] T038 在暫存測試專案複製 skill 後執行 `tools/run_trigger_evals.py`，修正描述直到 SC-007 達成；會產生費用，先告知維護者
- [ ] T039 在 Linux 上完整執行 `specs/002-personal-sdd-toolkit/quickstart.md`，記錄 SC-001、SC-003 的實際時間；對真實 `~/.claude/` 部署前先取得維護者同意
- [ ] T040 在 Windows 上完整執行 `specs/002-personal-sdd-toolkit/quickstart.md`，記錄 SC-001、SC-003 的實際時間，修正發現的差異（FR-028）；新 clone 先依前置條件設定 `user.email` 並安裝 hook；此步驟需要維護者在 Windows 機器上進行
- [ ] T041 取得維護者同意後，依 `specs/002-personal-sdd-toolkit/quickstart.md` 第 8 段在每台機器正式部署
- [ ] T042 `sdd-derive` 第一次實際使用後，在 `specs/002-personal-sdd-toolkit/plan.md` 記錄結果，未被使用則討論移除；同時記錄 SC-005 的實際比例

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 無相依；T001 到 T003 必須最先完成，並合成第一個 commit
- **Foundational (Phase 2)**: 依賴 Setup，會阻擋所有 user story
- **User Stories (Phase 3 到 7)**: 依賴 Foundational
- **Polish (Phase 8)**: 依賴所有 user story

### User Story Dependencies

- **US1**: Foundational 完成後即可開始
- **US2**: Foundational 完成後即可開始，不依賴 US1；`/sdd-init` 在其他專案使用時才需要 US1 部署
- **US3、US4**: 撰寫不互相依賴；驗收需要 US2。T028 先確認 skill 互相呼叫，因此建議 US3 先於 US4
- **US5**: 依賴 US1 的部署

### Within Each User Story

- 測試與驗收情境先於實作
- `tools/dotfiles.py` 依 T010 到 T013 的順序進行；`sdd_init.py` 依 T018 到 T020 的順序進行
- 同一個 `SKILL.md` 的任務依序進行，不可平行
- 每個任務完成就 commit

### Parallel Opportunities

- T004、T005 可平行
- T016、T022 可與 T018 到 T021 平行
- T024、T025 可與彼此平行，T029 可與 US3 任務平行
- US1 與 US2 在 Foundational 後可平行
- T037 可與其他 Polish 任務平行

---

## Parallel Example: User Story 3

```text
Task: "建立 tests/fixtures/sample-project/ 範例專案"
Task: "建立 tests/skills/sdd-derive/ 的 triggers.json 與 scenarios.md"
```

---

## Implementation Strategy

### MVP First

1. 完成 Phase 1 與 Phase 2，其中最小白名單最先完成。
2. 完成 US1。
3. **驗證**：用 `--target` 驗收部署與還原後，此 repo 就有可用的個人化 CLAUDE.md。

### Incremental Delivery

1. US1：個人化 CLAUDE.md 上線。
2. US2：新專案可一步導入 Spec Kit。
3. US3、US4：可以從既有專案導出，或透過討論產生文件。
4. US5：之後持續累積 skill。

每個階段都能單獨使用。最小白名單的 hook 能被略過，也不會隨 clone 帶走，此 repo 公開前必須另外完成 `001-repo-commit-guard`。

---

## Notes

- [P] 表示不同檔案且沒有未完成的相依任務
- 測試與開發中的驗收不得碰真實的 `~/.claude/`；只有 T039 到 T041 會改動它
- 測試資料只用假值與保留網域
- Windows 尚未驗證，完成 T040 前不得視為符合 FR-028
