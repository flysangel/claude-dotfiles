# Feature Specification: 持續整合測試與 E2E 測試

**Feature Branch**: `004-ci-e2e-tests`

**Created**: 2026-11-07

**Status**: Draft

**Input**: User description: "我需要有測試，也要有 E2E 測試"

## Clarifications

### Session 2026-11-07

- Q: 自動化測試在哪裡、何時跑？ → A: 每次 push 都由 CI 在 Linux 與 Windows 各跑一次。
- Q: E2E 驗證到什麼程度？ → A: 兩個系統都在 CI 自動跑；Windows 用 CI 提供的機器，排除既有工具來模擬乾淨環境。
- Q: E2E 多久跑一次？ → A: 每次 push。
- Q: CI 要不要在伺服器端跑入庫檢查？ → A: 要，一併納入，補上 `git push --no-verify` 的缺口。

### Session 2026-11-09

- Q: 會真的下載 Spec Kit 的網路測試要納入 CI 嗎？ → A: 只納入 Linux 的單元測試。
- Q: Windows E2E 怎麼模擬沒有 Git？ → A: 執行 Git 的解除安裝程式，真正從系統移除。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 每次 push 自動在兩個系統跑測試 (Priority: P1)

維護者 push 任何分支後，不用切換到另一台機器，就能在 GitHub 上看到全部自動化測試在 Linux 與 Windows 的結果。任一系統失敗時，維護者能從結果直接看出是哪個系統、哪一項測試。

**Why this priority**: 003 的 Windows 失敗是在維護者手動到 Windows 執行時才發現的；兩個系統都要支援是憲章原則 IV 的要求，但目前只有 Linux 會被經常測到。

**Independent Test**: push 一個讓某項測試只在 Windows 失敗的 commit，確認結果標示 Windows 失敗、Linux 通過，並指出該測試；修正後再 push，兩者都通過。

**Acceptance Scenarios**:

1. **Given** 任一分支有新的 push，**When** 測試完成，**Then** GitHub 上該 commit 顯示 Linux 與 Windows 各自的結果。
2. **Given** 某項測試只在一個系統失敗，**When** 維護者查看結果，**Then** 能看到失敗的系統與測試名稱。
3. **Given** Windows 上有兩種 PowerShell，**When** 測試執行，**Then** 入口腳本的測試在兩者都執行，任一失敗都算失敗。
4. **Given** 只能在特定系統執行的測試，**When** 測試完成，**Then** 結果列出每個系統略過的測試數；原本應在該系統執行的測試被略過時，算作失敗。

---

### User Story 2 - 每次 push 自動跑 E2E (Priority: P1)

每次 push 後，一行指令的完整流程會在沒有預裝工具的環境中實際跑一次：下載並安裝工具、取得 repo、部署、重跑、開發設定與解除。維護者不必再手動準備容器或 Windows 機器，就能知道真實安裝是否仍然可用。

**Why this priority**: 單元測試用假工具，無法發現官方安裝腳本、套件管理工具或作業系統的變化；003 的真實安裝驗證都靠手動，Windows 的自動安裝至今沒有驗證過。

**Independent Test**: push 後確認每個 E2E 環境都回報各階段的結果；把入口腳本的工具安裝暫時改壞並 push，確認 E2E 失敗並指出階段。

**Acceptance Scenarios**:

1. **Given** 一次 push，**When** E2E 完成，**Then** Linux 的 Ubuntu、Fedora、Arch 與版本下限環境，以及 Windows，都有各自的結果。
2. **Given** 環境中沒有 uv、git、Claude Code，**When** 執行一行指令，**Then** 三者都被安裝，部署完成。
3. **Given** 第一次設定完成，**When** 再執行一次，**Then** 部署內容與 clone 都沒有變化。
4. **Given** 加上開發選項與假的 noreply 地址，**When** 執行，**Then** commit 防護啟用，且能在該 clone 實際完成一次 commit。
5. **Given** 設定完成，**When** 執行解除，**Then** 部署前存在的設定檔回到原內容。
6. **Given** 目標目錄不是這個 repo，**When** 執行一行指令，**Then** 停止且回傳失敗，不執行該目錄內的程式。
7. **Given** 某個階段失敗，**When** 維護者查看結果，**Then** 能看出環境、階段與該階段的輸出。

---

### User Story 3 - 伺服器端的入庫檢查 (Priority: P2)

維護者用 `git push --no-verify` 略過本機檢查時，CI 仍會對推上去的內容做完整檢查，並在發現問題時標示失敗，讓維護者能在公開或合併前發現。

**Why this priority**: README 已把這個缺口列為已知限制。它只能事後發現、無法阻止內容進入遠端，所以排在測試之後。

**Independent Test**: 用 `--no-verify` 推一個含假 token 的分支，確認 CI 失敗並指出位置，且輸出不含 token 的完整值；刪除該分支。

**Acceptance Scenarios**:

1. **Given** 推上去的歷史含有違規內容，**When** CI 檢查完成，**Then** 結果為失敗，並列出位置與類型，不顯示機密原文。
2. **Given** CI 沒有本機識別清單，**When** 檢查完成，**Then** 結果明確說明這次沒有比對個人識別資訊，但其餘規則的違規仍會造成失敗。
3. **Given** 推上去的內容沒有違規，**When** 檢查完成，**Then** 結果為通過。

---

### Edge Cases

- **外部下載暫時失敗**（官方安裝腳本、套件來源）：E2E 結果要能看出失敗來自哪個下載來源，與程式本身的錯誤區分。暫時性的網路錯誤可以重試一次，仍失敗才算失敗。
- **Windows 的 CI 機器沒有 winget**：自動安裝 git 的情境無法驗證時，結果要明確列出未驗證的項目，不能當作通過或默默略過。
- **CI 機器已預裝工具**：E2E 要先讓既有的 uv、git、Claude Code 對一行指令不可見，並在結果中確認它們確實由這次安裝。
- **repo 是私有的**：E2E 要使用這次 push 的內容，不能依賴從公開網址下載腳本。
- **repo 公開後**：E2E 另外以 README 上的真實網址跑一次，涵蓋 003 的 T034。
- **Claude Code 未登入**：E2E 不登入，也不需要任何帳號或憑證；摘要出現登入提示是預期結果。
- **同一分支連續 push**：舊的執行可以取消，只保留最新 commit 的結果。

## Requirements *(mandatory)*

### Functional Requirements

**單元測試**

- **FR-001**: 每次 push 到任何分支，MUST 在 Linux 與 Windows 各執行一次全部自動化測試；需要網路的 Spec Kit 真實安裝測試只在 Linux 執行。
- **FR-002**: Windows 上 MUST 同時以內建的 Windows PowerShell 與新版 PowerShell 執行入口腳本的測試。
- **FR-003**: 結果 MUST 依系統分開顯示，並能看到失敗的測試名稱。
- **FR-004**: 結果 MUST 列出每個系統略過的測試；應在該系統執行的測試被略過時，MUST 視為失敗。
- **FR-005**: 會呼叫模型並產生費用的測試（skill 觸發評估）MUST NOT 在 CI 執行。

**E2E 測試**

- **FR-006**: 每次 push，MUST 在 Ubuntu、Fedora、Arch 的乾淨環境，以及 git 與 uv 版本下限的環境，各跑一次 E2E。
- **FR-007**: 每次 push，MUST 在 Windows 上跑一次 E2E，並在開始前讓既有的 uv、git、Claude Code 對一行指令不可見。
- **FR-008**: E2E MUST 依序涵蓋：首次設定（含工具安裝）、重跑沒有變化、開發設定與實際 commit、解除後還原、目標目錄不是這個 repo 時停止。
- **FR-009**: E2E MUST 使用這次 push 的內容；repo 公開後，MUST 另外以 README 上的真實網址執行首次設定。
- **FR-010**: E2E 的每個階段 MUST 有獨立的結果與輸出；失敗時 MUST 能看出環境與階段。
- **FR-011**: 無法在 CI 驗證的項目（例如沒有 winget 時的 git 自動安裝）MUST 明確列為未驗證，MUST NOT 算作通過。
- **FR-012**: E2E MUST NOT 需要任何帳號、權杖或其他機密，輸出 MUST NOT 含有真實 email；執行下載來的安裝腳本的環境 MUST NOT 能讀到 CI 提供的存取權杖。
- **FR-013**: 外部下載的暫時性失敗 MAY 重試一次；重試後仍失敗 MUST 算作失敗，並指出來源。

**入庫檢查**

- **FR-014**: 每次 push，MUST 對推上去的完整歷史與全部檔案執行入庫檢查。
- **FR-015**: 沒有本機識別清單時，入庫檢查 MUST 執行其餘全部規則，並在結果中說明未比對個人識別資訊；其餘規則有違規時 MUST 失敗。
- **FR-016**: 入庫檢查的輸出 MUST NOT 顯示機密的完整值。

**整體**

- **FR-017**: 同一分支有更新的 push 時，MUST 取消尚未完成的舊執行。
- **FR-018**: 新增的檔案 MUST 列入 `.repo-allowlist`，並通過 commit 防護。
- **FR-019**: README MUST 說明 CI 的內容與如何查看結果，並更新「已知限制」中與 CI 有關的說明，以及 003 的 Windows 驗收狀態。

### Key Entities

- **測試結果**：一次 push 在某個系統或環境的結果，包含通過、失敗、略過的測試，以及未驗證項目。
- **E2E 環境**：一個沒有預裝工具的作業系統環境；每個環境獨立執行同一套階段。
- **E2E 階段**：首次設定、重跑、開發設定、解除、失敗情境；每個階段有自己的結果與輸出。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 每次 push 後，維護者不需要使用其他機器，就能看到 Linux 與 Windows 的全部測試結果。
- **SC-002**: 從 push 到所有結果完成，在 20 分鐘內。
- **SC-003**: 故意讓一項測試只在 Windows 失敗時，CI 100% 標示為失敗，並指出系統與測試名稱。
- **SC-004**: 故意破壞工具安裝時，每個 E2E 環境 100% 失敗，並指出環境與階段。
- **SC-005**: 用 `--no-verify` 推上含假 token 的內容時，CI 100% 失敗，且輸出不含 token 的完整值。
- **SC-006**: 003 的 T033 中尚未驗證的 Windows 項目，除了明確列為未驗證者，全部由 CI 的 E2E 涵蓋。
- **SC-007**: 每月 40 次 push 以內，CI 用量不超過 GitHub Free 方案的額度（USD 12）；超過時要能在 README 查到如何減少執行。

## Assumptions

- CI 使用 GitHub Actions，因為 repo 已在 GitHub。Linux 的乾淨環境以容器提供；Windows 使用 GitHub 提供的機器。
- Windows 的 CI 機器並非全新安裝的 Windows；排除既有工具只能模擬乾淨環境，真正的新機器仍可能有差異。
- repo 目前為私有，CI 用量計入方案的免費額度，Windows 的計費倍率較高；實際用量在 plan 階段估算。
- E2E 使用假的 noreply 地址，不登入 Claude Code，不使用任何機密。
- 入庫檢查在遠端只能事後發現問題，無法阻止內容進入遠端；發現時仍要依憲章原則 I 處理。
- skill 觸發評估會產生費用，維持手動執行。

## Dependencies

- `specs/003-license-oneline-setup` 的入口腳本與 `tools/machine_setup.py`；E2E 會沿用它的 quickstart 情境。
- `specs/001-repo-commit-guard` 的 `tools/repo_guard.py`；沒有識別清單時的 CI 模式可能需要調整它的結束碼行為。
