---

description: "Task list for the public repo commit guard"
---

# Tasks: 公開 repo 入庫防護

**Input**: Design documents from `specs/001-repo-commit-guard/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: 包含測試任務。spec FR-022 要求每個功能都有自動化驗證，涵蓋應阻止與應放行的情況。

**Organization**: 依 user story 分組。多數既有檢查已由 002 的 `tools/check_allowlist.py` 完成，這裡只列缺口。

**Commit**: 每完成一項異動就在目前分支 commit，不直接提交到 `main`，也不 push，不得用 `--no-verify` 略過 hook。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可以平行進行（不同檔案，且不依賴未完成的任務）
- **[Story]**: 所屬的 user story（US1 到 US4）

## Path Conventions

路徑相對於 repo 根目錄。工具在 `tools/`，測試在 `tests/`，全部測試都在暫存 git repo 內進行。

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 把工具改成符合新範圍的名稱，且改名過程中防護不中斷

- [X] T001 用 `git mv` 把 `tools/check_allowlist.py` 改為 `tools/repo_guard.py`、`tests/test_check_allowlist.py` 改為 `tests/test_repo_guard.py`，更新 `HOOK_BODY`、`HOOK_MARKER` 與 `tests/test_content.py`、`README.md`、`docs/adding-a-skill.md` 的引用；`--install-hook` 與 `--uninstall-hook` 要認得舊版標記 `# managed-by: tools/check_allowlist.py`；commit 前先執行 `uv run tools/repo_guard.py --install-hook` 更新此 repo 的 hook，這些改動合成一個 commit

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 統一違規的資料結構，所有 story 都會用到

**⚠️ CRITICAL**: 完成前不要開始任何 user story

- [X] T002 在 `tests/test_repo_guard.py` 加入測試：每種違規都有 data-model 定義的類型代碼（`allowlist`、`binary`、`home-path`、`email`、`git-email`、`secret`、`identity`、`author`、`committer`）與修正方向；可豁免的違規顯示該行內容的 SHA-256 指紋；`allowlist` 與身分類沒有指紋；輸出不含被比對到的內容
- [X] T003 在 `tools/repo_guard.py` 改寫 `Violation` 與 `scan_text`，符合 T002 與 `specs/001-repo-commit-guard/contracts/repo-guard.md` 的輸出格式；`tests/test_content.py` 重用的規則保持可用

**Checkpoint**: 違規格式統一，user story 可以開始

---

## Phase 3: User Story 1 - Commit 時自動攔下機密與個資 (Priority: P1) 🎯 MVP

**Goal**: 補上 commit 訊息檢查、誤判例外、本機識別清單與啟用狀態

**Independent Test**: 暫存含假憑證、假 email、假路徑的檔案，並用違規的 commit 訊息與身分實際提交，確認都被阻止；乾淨內容正常完成

### Tests for User Story 1

- [X] T004 [US1] 在 `tests/test_repo_guard.py` 加入誤判例外測試：符合 `path`、`kind`、`line_sha256` 時通過；該行改變後失效；不能用於其他檔案或其他類型；`path` 不接受 glob；`reason` 為空、`line_sha256` 不是 64 位十六進位、JSON 格式錯誤時回傳 3；`allowlist`、`git-email`、`identity`、`author`、`committer` 不可豁免；`binary` 用整個檔案的雜湊值
- [X] T005 [US1] 在 `tests/test_repo_guard.py` 加入本機識別清單測試：不分大小寫比對檔案內容、commit 訊息、作者與提交者名稱；輸出不含清單內容；`#` 註解與空行略過；`REPO_GUARD_IDENTITY_FILE` 可覆寫路徑；清單不存在或沒有內容時，`--staged`、`--commit-msg`、`--all` 只提醒且不影響結束碼
- [X] T006 [US1] 在 `tests/test_repo_guard.py` 加入 `--commit-msg <file>` 測試：訊息含個人路徑、非 noreply 的 email、假 token 時不通過；乾淨訊息與 `Co-Authored-By` 的 noreply 地址通過；檔案無法讀取時回傳 3
- [X] T007 [US1] 在 `tests/test_repo_guard.py` 加入 hook 與 `--status` 測試：`--install-hook` 安裝 `pre-commit`、`commit-msg`、`pre-push`，重複執行結果相同；任一 hook 已被其他工具佔用時不覆蓋且回傳 1，也不留下部分安裝；舊版 hook 會被更新；`--uninstall-hook` 只移除自己的；`--status` 回報 `not-installed`、`enabled`、`unverified`（設定 `core.hooksPath` 時）

### Implementation for User Story 1

- [X] T008 [US1] 在 `tools/repo_guard.py` 實作讀取與驗證 `.repo-guard-exceptions.json`，移除 `FAKE_SECRET_DIR` 特例，依 `specs/001-repo-commit-guard/data-model.md` 的欄位規則處理；違規訊息提示如何記錄例外
- [X] T009 [US1] 建立 `.repo-guard-exceptions.json`，為 `tests/fixtures/sample-project/config/settings.py` 的假憑證加入例外，並把此檔加進 `.repo-allowlist`；執行 `uv run tools/repo_guard.py --all` 確認通過
- [X] T010 [US1] 在 `tools/repo_guard.py` 實作本機識別清單：預設 `~/.config/claude-dotfiles/identity.txt`，可用 `REPO_GUARD_IDENTITY_FILE` 覆寫；比對範圍含檔案內容與作者、提交者名稱；不存在或沒有內容時提醒
- [X] T011 [US1] 在 `tools/repo_guard.py` 實作 `--commit-msg <file>`，內容規則與檔案相同，略過 `#` 開頭的註解行
- [X] T012 [US1] 在 `tools/repo_guard.py` 實作安裝與移除三個 hook，一律寫入 `git rev-parse --git-common-dir` 下的 `hooks/`；先檢查全部再寫入，避免部分安裝；內容不含絕對路徑，使用 LF
- [X] T013 [US1] 在 `tools/repo_guard.py` 實作 `--status`，第一行是狀態，之後列出 `core.hooksPath`、本機識別清單與作者 email 的情況
- [X] T014 [US1] 依 `specs/001-repo-commit-guard/quickstart.md` 第 2 到 5 段在此 repo 驗收，確認帳號層 dispatch 會轉交 `commit-msg`（research 第 3 節待確認項目），並記錄 SC-003、SC-006 的實際時間；此階段不測 `pre-push`

**Checkpoint**: Commit 防護可獨立運作

---

## Phase 4: User Story 2 - 只有白名單內的檔案能入庫 (Priority: P1)

**Goal**: 確認 002 的白名單行為涵蓋 spec 的驗收情境，補齊缺少的測試

**Independent Test**: 暫存白名單外的檔案並提交，確認被阻止；列入白名單後可完成

### Tests for User Story 2

- [X] T015 [US2] 在 `tests/test_repo_guard.py` 補上尚未涵蓋的情況：被 `.gitignore` 排除但用 `git add -f` 加入的檔案不通過；把檔案改名到白名單外不通過；把白名單外的已追蹤檔案刪除可以通過；此 repo 的 `.repo-allowlist` 沒有比對到 `.credentials.json`、`history.jsonl`，也沒有 `**` 這種涵蓋全部路徑的規則

**Checkpoint**: 白名單可獨立運作

---

## Phase 5: User Story 3 - 公開前檢查完整歷史與全部檔案 (Priority: P2)

**Goal**: 對完整歷史執行同一套檢查，並在每次 push 前自動執行

**Independent Test**: 在歷史中留下已刪除的假憑證，確認檢查回報其 commit 與檔案；真實 `git push` 到本機測試 remote 時被阻止

### Tests for User Story 3

- [X] T016 [US3] 在 `tests/test_repo_guard.py` 加入 `--history` 測試：已刪除的假憑證回報 commit 前 12 碼與檔案；舊 commit 的作者或提交者 email 不是 noreply 時不通過；commit 訊息違規不通過；歷史中白名單外的檔案不通過；其他分支與 tag 上的 commit 也會掃到；例外靠內容雜湊對舊版本同樣有效；乾淨 repo 通過；最後一行明確寫出 `通過` 或 `不通過`；輸出不含機密完整值
- [X] T017 [US3] 在 `tests/test_repo_guard.py` 加入測試：`--history` 在本機識別清單不存在或沒有內容時回傳 3；含清單內容的舊 commit、作者名稱不通過；以及端對端測試：用 `--no-verify` 提交違規內容後，`git push` 到暫存 bare repo 被阻止，乾淨時可以 push

### Implementation for User Story 3

- [X] T018 [US3] 在 `tools/repo_guard.py` 實作 `--history`：用 `git rev-list --all` 走訪 commit，檢查身分與訊息；用 `git diff-tree -r --root --no-renames` 取得每個 commit 引入的檔案版本，同一個 blob 只掃一次；同時檢查所有已追蹤檔案；白名單與例外都以目前版本為準；只回報，不修改歷史
- [X] T019 [US3] 在 `tools/repo_guard.py` 讓 `--history` 套用本機識別清單規則，並讓 `pre-push` hook 呼叫它；確認 hook 不會因為讀取 stdin 而卡住
- [X] T020 [US3] 在此 repo 執行 `uv run tools/repo_guard.py --history`，記錄耗時；依結果修正問題，發現真實機密時停止並回報維護者，不得自行改寫歷史；此階段可用暫存的 `REPO_GUARD_IDENTITY_FILE` 測試

**Checkpoint**: 完整檢查可獨立運作

---

## Phase 6: User Story 4 - 檢視現有設定並判斷可否共用 (Priority: P2)

**Goal**: 為 `settings.json` 的每個頂層項目提供分類，不外洩任何設定值

**Independent Test**: 用含假 token、絕對路徑與一般偏好的設定檔執行，確認分類正確、原始檔沒變、報告沒有假 token

### Tests for User Story 4

- [ ] T021 [P] [US4] 建立 `tests/test_review_settings.py`，涵蓋：值符合憑證規則或鍵名像憑證時標為 `含機密`；值含個人路徑時標為 `機器專屬`；已知安全鍵標為 `可共用`；未知鍵標為 `待判斷`；已知安全鍵的值觸發規則時不得標為可共用；巢狀值取最嚴重的分類並列出鍵路徑；輸出不含任何設定值；可疑鍵名會被遮蔽；原始檔不變；檔案不存在或 JSON 無效時回傳 3 且訊息不含檔案內容；每個頂層項目都有一筆分類

### Implementation for User Story 4

- [ ] T022 [US4] 依 `specs/001-repo-commit-guard/contracts/review-settings.md` 建立 `tools/review_settings.py`，重用 `tools/repo_guard.py` 的規則與本機識別清單，PEP 723 宣告版本需求，只用標準庫
- [ ] T023 [US4] 依 `specs/001-repo-commit-guard/quickstart.md` 第 6 段對真實的 `~/.claude/settings.json` 執行，比對執行前後的雜湊值，並把分類結果回報維護者；報告不得寫入 repo

**Checkpoint**: 所有 user story 都可獨立運作

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 文件同步與公開前的最終確認

- [ ] T024 [P] 更新 `README.md`：安裝步驟改為 `repo_guard.py` 與本機識別清單；說明誤判例外、`--status`、`--history`、`review_settings.py`；修改已知限制中關於 commit 檢查的描述
- [ ] T025 [P] 把 `specs/002-personal-sdd-toolkit/quickstart.md` 的 `check_allowlist.py` 指令改為 `repo_guard.py`，並在 `specs/002-personal-sdd-toolkit/contracts/allowlist.md` 開頭註明已由 `specs/001-repo-commit-guard/contracts/repo-guard.md` 取代
- [ ] T026 請維護者建立本機識別清單 `~/.config/claude-dotfiles/identity.txt`，內容由維護者決定，你不得代填或讀取後輸出
- [ ] T027 執行 `uv run tools/repo_guard.py --history` 與 `gitleaks git --no-banner --redact`，確認此 repo 目前都通過；gitleaks 回報時，判斷為誤判或真實機密後回報維護者
- [ ] T028 取得維護者同意後，建立 GitHub **私有** repo 並 push；設定 remote 與建立 repo 都是對外操作，事先確認名稱與可見性
- [ ] T029 請維護者在 Windows 機器 clone 後，完成 `specs/001-repo-commit-guard/quickstart.md` 與 `specs/002-personal-sdd-toolkit/` 的 T040，修正發現的差異（FR-019）
- [ ] T030 在包含 Windows 修正的最新歷史上再次執行 T027 的兩項檢查，結果與公開決定一起回報維護者（SC-007）；是否公開由維護者決定，不得自行改變 repo 可見性

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 無相依；T001 要在同一個 commit 內更新 hook，否則下一次 commit 會失敗
- **Foundational (Phase 2)**: 依賴 Setup，會阻擋所有 user story
- **User Stories (Phase 3 到 6)**: 依賴 Foundational
- **Polish (Phase 7)**: 依賴所有 user story

### User Story Dependencies

- **US1**: Foundational 完成後即可開始
- **US2**: 不依賴其他 story，但要在 T009 把例外檔加進白名單後才驗收
- **US3**: 依賴 US1 的例外、識別清單與 hook 安裝
- **US4**: 只重用 US1 的識別清單與既有規則，可與 US2、US3 平行

### Within Each User Story

- 測試先於實作
- `tools/repo_guard.py` 與 `tests/test_repo_guard.py` 是共用檔案，涉及它們的任務要依序進行
- 每個任務完成就 commit

### Parallel Opportunities

- T021 可與 US3 的任務平行
- T024、T025 可平行
- 其他任務都會改到 `tools/repo_guard.py` 或 `tests/test_repo_guard.py`，要依序進行

---

## Parallel Example: Polish

```text
Task: "更新 README.md 的安裝步驟與防護說明"
Task: "更新 002 的 quickstart 與 allowlist contract 引用"
```

---

## Implementation Strategy

### MVP First

1. 完成 Phase 1 與 Phase 2。
2. 完成 US1。
3. **驗證**：實際 commit 確認訊息、例外與識別清單都有作用。

### Incremental Delivery

1. US1：commit 防護完整。
2. US2：白名單情境都有測試。
3. US3：完整歷史與 push 前檢查，具備公開前確認的能力。
4. US4：可以判斷現有設定能否共用。
5. 依 T026 到 T030 走到公開決定。

---

## Notes

- 公開與推送都是對外操作，T028、T030 要維護者另外同意
- 測試資料只用假值與保留網域，違規樣本在執行時組合
- 本機識別清單的內容不得出現在輸出、對話或 repo 中
- `git push --no-verify` 仍能略過檢查，要靠之後的 CI 補上，不在此功能範圍內
- `LICENSE` 與 Spec Kit 檔案的授權條件不在此功能範圍內，公開前要另外決定
