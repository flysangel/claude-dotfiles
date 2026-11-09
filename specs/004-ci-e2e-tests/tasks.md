---

description: "Task list for CI and E2E tests"
---

# Tasks: 持續整合測試與 E2E 測試

**Input**: Design documents from `specs/004-ci-e2e-tests/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: 包含測試任務。這個功能的產出就是測試；新增的 Python 邏輯有單元測試，workflow 有靜態檢查，E2E 驅動在本機容器實際執行。

**Organization**: 依 user story 分組。US1、US2、US3 互相獨立，都只依賴 Foundational 的 workflow 骨架。

**Push**: 每完成一項異動就在目前分支 commit，不直接提交到 `main`，不得用 `--no-verify` 略過 hook（T036 的故意違規除外，且要維護者同意）。**push 一律要維護者另外同意**，T033 到 T037 都會用到 CI 額度。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可以平行進行（不同檔案，且不依賴未完成的任務）
- **[Story]**: 所屬的 user story（US1 到 US3）

## Path Conventions

路徑相對於 repo 根目錄。workflow 在 `.github/workflows/`，E2E 驅動在 `tests/e2e/`。E2E 驅動會真的安裝工具並改動家目錄，只能在拋棄式環境執行，不得在開發機上直接執行。

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 讓新檔案能通過 commit 防護

- [ ] T001 在 `.repo-allowlist` 加入 `.github/**`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: workflow 骨架與它的靜態檢查，三個 story 都會加 job 進去

**⚠️ CRITICAL**: 完成前不要開始任何 user story

- [ ] T002 建立 `tests/test_ci_workflow.py`，以標準庫（文字比對，不依賴 YAML 套件）檢查 `.github/workflows/ci.yml`：觸發包含 `push` 與 `workflow_dispatch`；`concurrency` 以 `github.ref` 分組且 `cancel-in-progress: true`（FR-017）；`permissions` 只有 `contents: read`；不含 `secrets.`（FR-012）；每個 `uses:` 都固定到 40 碼 commit SHA，且只來自 `actions/checkout` 與 `astral-sh/setup-uv`；每個 `actions/checkout` 都設 `persist-credentials: false`（FR-012）；不含 `run_trigger_evals`（FR-005）
- [ ] T003 建立 `.github/workflows/ci.yml` 的骨架：名稱、觸發、`concurrency`、`permissions`，先放一個最小的 `unit-linux` job；查出 `actions/checkout` 與 `astral-sh/setup-uv` 目前穩定版的 commit SHA 並固定，以註解標示版本；讓 T002 通過，並執行 `uv tool run check-jsonschema --builtin-schema vendor.github-workflows .github/workflows/ci.yml`

**Checkpoint**: workflow 合法且符合共通限制

---

## Phase 3: User Story 1 - 每次 push 自動在兩個系統跑測試 (Priority: P1) 🎯 MVP

**Goal**: push 後能在 GitHub 看到 Linux 與 Windows 的全部測試結果，該跑的測試被略過時算失敗

**Independent Test**: push 一個只在 Windows 失敗的測試，確認 `unit-windows` 失敗並指出測試名稱，`unit-linux` 通過

### Tests for User Story 1

- [ ] T004 [P] [US1] 建立 `tests/test_gates.py`，依 `specs/004-ci-e2e-tests/contracts/test-gates.md` 的真值表測試 `requires(group, condition, reason)`：未要求且條件成立時執行；未要求且條件不成立時略過並帶 `reason`；要求且條件成立時執行；要求且條件不成立時每個測試都失敗，訊息含群組名稱；`REQUIRED_TEST_GROUPS` 以逗號分隔、未設定等同空集合
- [ ] T005 [P] [US1] 在 `tests/test_ci_workflow.py` 加入單元測試 job 的檢查：`unit-linux` 設定 `REQUIRED_TEST_GROUPS=setup-sh,powershell`、`SETUP_PS1_TESTS=1`、`SETUP_PS1_SHELL=pwsh`、`RUN_NETWORK_TESTS=1`；`unit-windows` 設定 `REQUIRED_TEST_GROUPS=powershell`，且 `SETUP_PS1_SHELL` 的 `powershell` 與 `pwsh` 都有執行；測試都用 `-v`（FR-001 到 FR-004）

### Implementation for User Story 1

- [ ] T006 [US1] 建立 `tests/gates.py`，實作 `requires`，讓 T004 通過
- [ ] T007 [US1] 在 `tests/test_setup_scripts.py` 把 `SetupShTestCase` 的 `unittest.skipUnless` 改為 `requires("setup-sh", ...)`
- [ ] T008 [US1] 在 `tests/test_setup_scripts_windows.py` 把 `WindowsPreflightTests`、`WindowsToolInstallTests`、`WindowsCloneTests`、`WindowsSessionTests` 的 `unittest.skipUnless` 改為 `requires("powershell", ...)`，`NonWindowsTests` 保持 `skipUnless`；加上 `SETUP_PS1_SHELL`：值為 `powershell` 或 `pwsh` 時只用該程式，找不到視為條件不成立，未設定時沿用先找 `powershell` 再找 `pwsh`；非 Windows 時在測試環境補上 `ProgramFiles` 與 `LOCALAPPDATA`，否則 `setup.ps1` 的 `Join-Path` 會出錯
- [ ] T009 [US1] 在 `.github/workflows/ci.yml` 完成 `unit-linux`：checkout 取完整歷史、安裝 uv、依 contract 設定環境變數並執行 `uv run -m unittest discover -s tests -v`
- [ ] T010 [US1] 在 `.github/workflows/ci.yml` 新增 `unit-windows`：先以 `SETUP_PS1_SHELL=powershell` 跑全部測試，再以 `SETUP_PS1_SHELL=pwsh` 跑 `tests.test_setup_scripts_windows`，兩步都要執行且任一失敗都算失敗，讓 T005 通過
- [ ] T011 [US1] 在 `.github/workflows/ci.yml` 的兩個單元測試 job，把測試輸出存下並把通過、失敗、略過的數量與略過的測試名稱寫入 `$GITHUB_STEP_SUMMARY`（FR-003、FR-004），測試失敗時仍要寫出
- [ ] T012 [US1] 完成 `specs/004-ci-e2e-tests/quickstart.md` 第 1 段，確認在沒有 PowerShell 的機器上 `REQUIRED_TEST_GROUPS=powershell` 會失敗

**Checkpoint**: 單元測試的 CI 內容完整，等第一次 push 驗證

---

## Phase 4: User Story 2 - 每次 push 自動跑 E2E (Priority: P1)

**Goal**: 每次 push 在沒有預裝工具的環境實際跑完一行指令的完整流程

**Independent Test**: push 後每個環境都回報五個階段的結果；把工具安裝改壞時，每個環境的 `setup` 都失敗並指出來源

### Tests for User Story 2

- [ ] T013 [P] [US2] 在 `tests/test_ci_workflow.py` 加入 E2E job 的檢查：`e2e-linux` 的 matrix 含 `ubuntu`、`fedora`、`arch`、`minimum`，映像為 `ubuntu:24.04`、`fedora:latest`、`archlinux:latest`、`debian:10`；`e2e-windows` 使用 `windows-latest` 且以 `windows.ps1` 執行；公開後的步驟條件含 repo 非私有且 `refs/heads/main`
- [ ] T014 [P] [US2] 在 `tests/test_setup_scripts.py` 的 `StaticTests` 加入驅動腳本的靜態檢查：`tests/e2e/windows.ps1` 只含 ASCII；兩支驅動都含五個階段名稱 `setup`、`rerun`、`dev`、`remove`、`refuse`，開發設定使用的 email 都是 `@users.noreply.github.com` 的假地址；`tools/setup.sh` 與 `tools/setup.ps1` 的下載失敗訊息都含 `cannot download`

### Implementation for User Story 2

- [ ] T015 [US2] 建立 `tests/e2e/linux.sh`（`bash tests/e2e/linux.sh <環境名稱> <bare repo 路徑>`），依 data-model 的判定依序執行 `setup`、`rerun`、`dev`、`remove`、`refuse`。開始時把 bare repo 複製到家目錄再使用，避免擁有者不同造成 dubious ownership；結果行格式固定為 `E2E <環境> <階段> <PASS|FAIL|UNVERIFIED> <說明>`，只寫到標準輸出；每階段輸出用 `::group::` 折疊；前一階段失敗時後續階段記為 `FAIL`，說明為「前一階段失敗」；任一 `FAIL` 時結束碼 1；`setup` 失敗且輸出含 `cannot download`、`apt-get failed`、`dnf failed`、`pacman failed` 或 `winget failed` 時重試一次，仍失敗要在說明寫出來源（FR-013）；`E2E_SETUP_URL` 有值時 `setup` 改用該網址；設定前放入 `~/.claude/CLAUDE.md` 與 `~/.claude/rules/`，供 `remove` 比對；比對 `rerun` 雜湊時排除 Claude Code 自己寫入的檔案
- [ ] T016 [US2] 用 podman 依 `specs/004-ci-e2e-tests/research.md` 第 5 節準備四個環境（加 `--cgroups=disabled`），實際執行 `tests/e2e/linux.sh`，完成 quickstart 第 2 段；修正發現的問題，並把每個環境的結果與耗時記錄到 `specs/004-ci-e2e-tests/research.md`
- [ ] T017 [US2] 建立 `tests/e2e/windows.ps1`（`-BareRepo`、`-SetupUrl`），流程與結果格式同 T015：開始前先確認 winget 是否可用（依 research 第 6 節），可用時執行 `C:\Program Files\Git\unins000.exe /VERYSILENT /NORESTART` 解除安裝 Git，並從 `PATH` 移除含 `git.exe`、`uv.exe`、`claude.exe` 的目錄，確認三者都找不到；winget 不可用時保留 git，並輸出 `E2E windows setup-git-install UNVERIFIED no winget on this machine` 這一行，可用且 `setup` 通過時該項為 `PASS`；同時把 `tools/setup.ps1` 官方腳本失敗的訊息改成含 `cannot download` 與網址；入口腳本以 Windows PowerShell 5.1 的子程序執行；只含 ASCII，訊息用英文
- [ ] T018 [US2] 在 PowerShell 容器內解析 `tests/e2e/windows.ps1`，確認沒有語法錯誤（`[System.Management.Automation.Language.Parser]::ParseFile`）；實際行為要到 T033 的第一次 push 才驗證
- [ ] T019 [US2] 在 `.github/workflows/ci.yml` 新增 `e2e-linux` matrix：以完整歷史的 checkout 建立 bare repo，`docker run` 只唯讀掛載 bare repo 與 `tests/e2e/`，不掛載 checkout，依環境準備（ubuntu 安裝 `curl`、`sudo` 並建立使用者；minimum 依 research 第 5 節）後執行驅動；把容器標準輸出中的 `E2E ` 結果行由 runner 上的步驟寫入 `$GITHUB_STEP_SUMMARY`；設定 `fail-fast: false`，讓其他環境繼續跑
- [ ] T020 [US2] 在 `.github/workflows/ci.yml` 新增 `e2e-windows`：先建立 bare repo，再以 `powershell -NoProfile -ExecutionPolicy Bypass -File tests\e2e\windows.ps1` 執行，之後的步驟不得依賴 git；讓 T013 通過
- [ ] T021 [US2] 在 `.github/workflows/ci.yml` 加入公開後的真實網址步驟：只在 repo 非私有且 push 到 `main` 時，以 README 的一行指令各跑一次 `ubuntu-public` 與 `windows-public`（FR-009）

**Checkpoint**: E2E 的 CI 內容完整，Linux 驅動已實測，Windows 驅動等第一次 push 驗證

---

## Phase 5: User Story 3 - 伺服器端的入庫檢查 (Priority: P2)

**Goal**: `--no-verify` 略過本機檢查時，CI 仍能發現違規

**Independent Test**: 用 `--no-verify` 推一個含假 token 的分支，CI 失敗並指出位置，輸出不含完整值

### Tests for User Story 3

- [ ] T022 [US3] 在 `tests/test_repo_guard.py` 加入 `--history --without-identity` 的測試：沒有識別清單時執行其餘規則、第一行說明未比對個人識別資訊、乾淨歷史結束碼 0；歷史含假 token 時結束碼 1 且輸出不含完整值；有識別清單時也不讀取它，清單內容不會造成違規；與 `--history` 以外的模式併用時結束碼 3；不加選項時沒有清單仍為結束碼 3

### Implementation for User Story 3

- [ ] T023 [US3] 在 `tools/repo_guard.py` 實作 `--without-identity`，依 `specs/004-ci-e2e-tests/contracts/test-gates.md`，讓 T022 通過
- [ ] T024 [US3] 更新 `specs/001-repo-commit-guard/contracts/repo-guard.md`，加入 `--without-identity` 的說明
- [ ] T025 [P] [US3] 在 `tests/test_ci_workflow.py` 加入 `guard` job 的檢查：執行 `repo_guard.py --history --without-identity`，checkout 取完整歷史（`fetch-depth: 0`）
- [ ] T026 [US3] 在 `.github/workflows/ci.yml` 新增 `guard` job，讓 T025 通過

**Checkpoint**: 三類檢查的 workflow 都完成

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 文件、整體驗證與實際在 GitHub 上的驗收

- [ ] T027 在 `README.md` 新增 CI 段落：有哪些 job、到哪裡看結果、每次 push 的預估用量與免費額度；寫明超過額度時可以考慮的兩種做法（只改文件時略過 E2E、Windows E2E 只在 `main` 跑），並註明這兩種做法要維護者決定
- [ ] T028 更新 `README.md` 的「已知限制」：`git push --no-verify` 的說明改為 CI 能事後發現但無法阻止；CI 沒有比對本機識別清單；Windows E2E 在 CI 機器上模擬乾淨環境，不等於真正的新機器
- [ ] T029 [P] 在 `tests/test_content.py` 加入檢查：`README.md` 提到 CI 段落，且 `.repo-allowlist` 含 `.github/**`
- [ ] T030 執行 `uv run -m unittest discover -s tests`、`uv run tools/repo_guard.py --all` 與 `uv tool run check-jsonschema --builtin-schema vendor.github-workflows .github/workflows/ci.yml`，全部通過
- [ ] T031 確認這個功能沒有改動 `home/`（`git diff --stat main...HEAD -- home/` 沒有輸出），因此不需要執行 `/doctor prompt-audit`；有改動時就要執行
- [ ] T032 依憲章 Constitution Check 再確認一次：新增檔案都在白名單內，workflow 與驅動腳本不含真實 email、機密或絕對的個人路徑
- [ ] T033 取得維護者同意後 push 分支，完成 `specs/004-ci-e2e-tests/quickstart.md` 第 3 段的觀察；把實際分鐘數更新到 `specs/004-ci-e2e-tests/research.md` 第 7 節與 `README.md` 的 CI 段落；估算超過額度時回報維護者決定（SC-007）
- [ ] T034 依第一次執行的結果修正 `tests/e2e/windows.ps1`、`.github/workflows/ci.yml` 與 `tools/setup.ps1`，每次修正 push 前都要維護者同意；把 winget 是否可用記錄到 `specs/004-ci-e2e-tests/research.md` 第 6 節
- [ ] T035 確認 `e2e-windows` 的五個階段結果，把 Windows 上已由 CI 驗證的項目記錄到 `specs/003-license-oneline-setup/research.md` 第 14 節，並更新 `README.md` 的「目前狀態」；CI 涵蓋 003 T033 尚未驗證的項目後，把 `specs/003-license-oneline-setup/tasks.md` 的 T033 標為完成，無法涵蓋的項目明確列為未驗證（SC-006）
- [ ] T036 取得維護者同意後，完成 `specs/004-ci-e2e-tests/quickstart.md` 第 4 段的四個故意失敗情境，每項都用獨立分支，驗證後本機與遠端的分支都要刪除，否則 `--history` 會讓之後的 push 失敗；含假 token 的分支要用測試專用的假值，結果記錄到 `specs/004-ci-e2e-tests/research.md`（SC-003、SC-004、SC-005）
- [ ] T037 公開後（維護者另外決定），完成 `specs/004-ci-e2e-tests/quickstart.md` 第 5 段，同時完成 `specs/003-license-oneline-setup/tasks.md` 的 T034

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup（Phase 1）**：沒有前置
- **Foundational（Phase 2）**：依賴 Setup；擋住全部 story
- **US1、US2、US3（Phase 3 到 5）**：都只依賴 Foundational，彼此獨立，但都會編輯 `.github/workflows/ci.yml` 與 `tests/test_ci_workflow.py`，不能同時改
- **Polish（Phase 6）**：T027 到 T032 依賴全部 story；T033 到 T036 依賴 push；T037 依賴 repo 公開

### User Story Dependencies

```text
Setup → Foundational → US1、US2、US3（順序不限）→ Polish → T033（第一次 push）→ T034、T035、T036 → 公開 → T037
```

### Within Each User Story

- 測試先寫，確認失敗後再實作
- 同一個檔案的任務依序進行

## Parallel Opportunities

- US1：T004（`tests/test_gates.py`）與 T005（`tests/test_ci_workflow.py`）
- US2：T013（`tests/test_ci_workflow.py`）與 T014（`tests/test_setup_scripts.py`），T015（Linux 驅動）與 T017（Windows 驅動）為不同檔案，但 T017 要等 T015 定下流程才方便對照
- US3：T025 可以和 T022 同時進行，但要避開其他 story 正在改的 `tests/test_ci_workflow.py`
- Polish：T029 與 T027、T028

### Parallel Example: User Story 1

```text
T004（tests/test_gates.py）與 T005（tests/test_ci_workflow.py）同時寫測試
T006 → T007 → T008（測試閘門）
T009 → T010 → T011（workflow，同一個檔案，依序）
```

## Implementation Strategy

### MVP First

1. 完成 Setup、Foundational 與 US1：這已經能解決「Windows 問題要手動才發現」。
2. push 一次，確認 CI 跑得起來、Windows 測試真的有執行，並取得實際用量。
3. 用實際用量確認每次 push 跑 E2E 是否負擔得起，再繼續。

### Incremental Delivery

1. US2：先做 Linux 驅動並在本機容器實測，再做 Windows。
2. US3：改動小，可以穿插在任何時候。
3. T035 把 CI 結果回填 003 的驗收，T037 在公開後完成。

---

## Notes

- 每次 push 都會花 CI 額度，且都要維護者同意；能在本機驗證的項目先在本機做完
- `tests/e2e/windows.ps1` 會解除安裝系統上的 Git，只能在 CI runner 上執行
- workflow 的行為無法在本機驗證，第一次 push 很可能需要修正
- 故意違規的分支驗證後要立刻刪除，假 token 仍視為違規內容，只能用測試專用的假值
