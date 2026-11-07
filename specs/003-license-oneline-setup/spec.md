# Feature Specification: 授權聲明與一行指令設定

**Feature Branch**: `003-license-oneline-setup`

**Created**: 2026-11-06

**Status**: Draft

**Input**: User description: "補 LICENSE，還要補一下 linux windows 一鍵設定"

## Clarifications

### Session 2026-11-06

- Q: LICENSE 用哪一種授權？ → A: Apache-2.0。
- Q: 一鍵設定從哪裡開始？ → A: 貼一行遠端指令，連取得 repo 都包辦。
- Q: 缺少必要工具時怎麼處理？ → A: uv、git、Claude Code 全部自動安裝。
- Q: 一鍵設定涵蓋哪些步驟？ → A: 預設只部署，加選項才做開發設定（公開安全的 email 與 commit 防護）。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 新機器貼一行就完成設定 (Priority: P1)

使用者拿到一台全新的 Linux 或 Windows 機器，貼上 README 提供的一行指令。指令會補齊缺少的工具、取得 repo，並把個人化設定部署到 `~/.claude/`，最後告訴使用者完成了什麼、下一步是什麼。

**Why this priority**: 這是憲章原則 IV「安裝只需一個指令」的要求；目前 README 要先手動裝好工具、clone，再跑多行指令。

**Independent Test**: 在只有作業系統的 Linux 與 Windows 乾淨環境各貼一次指令，確認設定已部署，且部署狀態回報為 `clean`。

**Acceptance Scenarios**:

1. **Given** 乾淨的 Linux 或 Windows 機器，**When** 使用者貼上對應的一行指令，**Then** uv、git、Claude Code 都可使用，repo 已取得，`~/.claude/` 已有部署內容。
2. **Given** 已具備部分工具的機器，**When** 使用者執行指令，**Then** 只安裝缺少的工具，既有工具不被更動。
3. **Given** 設定完成，**When** 指令結束，**Then** 摘要列出這次安裝的工具、repo 位置、部署結果與尚未完成的事項（例如登入 Claude Code）。
4. **Given** 已完成設定且沒有更新，**When** 再次執行指令，**Then** 沒有任何變更，並回報已是最新狀態。
5. **Given** repo 有新版內容且本機 clone 沒有改動，**When** 再次執行指令，**Then** 更新到新版並重新部署。
6. **Given** `~/.claude/` 已有 `CLAUDE.md`，**When** 執行指令，**Then** 原檔先備份才被取代，與現有部署行為相同。

---

### User Story 2 - 專案有明確的授權 (Priority: P1)

想使用或參考這個 repo 的人，能在根目錄看到 Apache-2.0 授權，也能看到 repo 內含的 Spec Kit 檔案來自 MIT 授權的上游。

**Why this priority**: 沒有授權聲明時，別人依法沒有使用權；這也是 `specs/001-repo-commit-guard/tasks.md` 留待公開前決定的事項。它不依賴其他 User Story，可以最先完成。

**Independent Test**: 確認根目錄有 Apache-2.0 全文、第三方聲明涵蓋 Spec Kit，且兩個檔案都能通過 commit 防護。

**Acceptance Scenarios**:

1. **Given** repo 根目錄，**When** 讀者開啟 `LICENSE`，**Then** 內容是未經改動的 Apache-2.0 全文。
2. **Given** repo 內含 Spec Kit 的檔案，**When** 讀者查看第三方聲明，**Then** 能看到這些檔案的路徑、上游來源、MIT 條款與原著作權聲明。
3. **Given** 新增的授權檔案，**When** 維護者提交，**Then** 白名單與內容掃描都通過，且內容不含 email。
4. **Given** 讀者開啟 README，**When** 查看授權段落，**Then** 能看到授權名稱與上述兩個檔案的連結。

---

### User Story 3 - 維護者一併完成開發設定 (Priority: P2)

維護者在指令上加開發選項，並提供公開安全的 email，就能在部署之外同時設定這個 clone 的提交身分與 commit 防護，不用再手動跑額外指令。

**Why this priority**: 這些設定每個 clone 都要做一次，漏掉就可能把個人 email 帶進公開歷史；但只使用設定、不開發的機器不需要它。

**Independent Test**: 加上開發選項與 noreply email 執行後，確認這個 clone 的提交身分正確、防護已啟用；不加選項時確認兩者都未被更動。

**Acceptance Scenarios**:

1. **Given** 開發選項與 noreply email，**When** 執行指令，**Then** email 只寫入這個 clone 的本機設定，commit 防護已啟用，部署也完成。
2. **Given** 開發選項，但 email 不是 noreply 地址，**When** 執行指令，**Then** 開發設定不執行，訊息說明可接受的格式。
3. **Given** 開發選項但未提供 email，且這個 clone 尚未設定 noreply 地址，**When** 執行指令，**Then** 開發設定不執行，訊息說明如何提供。
4. **Given** 沒有開發選項，**When** 執行指令，**Then** 不更動提交身分，也不安裝 commit 防護。
5. **Given** commit 防護的 hook 位置已被其他工具佔用，**When** 使用開發選項，**Then** 不覆蓋既有 hook，並回報未啟用的原因。
6. **Given** 開發選項，且本機識別清單不存在，**When** 執行指令，**Then** 其餘設定照常完成，摘要提示如何建立清單。

---

### User Story 4 - 解除設定 (Priority: P2)

使用者想退回時，用一個指令解除部署與開發設定，`~/.claude/` 回到設定前的狀態，並清楚知道哪些東西留在機器上。

**Why this priority**: 憲章原則 IV 要求能還原。部署本身已有 `undeploy`，這裡補上一致的入口與開發設定的還原。

**Independent Test**: 記錄 `~/.claude/` 的狀態，設定後再解除，比對內容一致；確認摘要列出保留項目。

**Acceptance Scenarios**:

1. **Given** 已完成設定，**When** 使用者執行解除指令，**Then** `~/.claude/` 回到設定前的內容。
2. **Given** 曾使用開發選項，**When** 解除，**Then** commit 防護被移除，提交身分回到設定前的值。
3. **Given** 設定時曾自動安裝工具，**When** 解除，**Then** 工具與 clone 都保留，摘要列出它們與移除方式。

### Edge Cases

- **網路中斷或下載失敗**：回報失敗的步驟並停止，不留下半完成的部署；修復後重新執行可以接續完成。
- **安裝工具需要系統管理員權限**：只在安裝 git 這類系統工具時才要求，由作業系統提示；被拒絕或無法取得時，停止並列出手動安裝方式。指令本身不要求以系統管理員身分執行，也不保存任何密碼。
- **沒有可用的套件管理工具**：無法自動安裝該工具時，停止並列出手動安裝方式。
- **剛裝好的工具還不在目前 shell 的路徑上**：同一次執行仍要能繼續完成，並提示使用者是否需要開新的終端機。
- **目標位置已存在但不是這個 repo**：停止，不覆蓋也不刪除。
- **本機 clone 有未提交的改動或與遠端分岔**：不更新也不覆寫 clone，說明狀況後停止。
- **`~/.claude/` 有同名且不受管的 skill**：沿用現有部署行為停止，訊息說明如何用 `--force` 選項繼續。
- **工具已存在但版本過舊，無法執行後續步驟**：不自動升級使用者既有的工具，回報所需版本後停止。
- **在 macOS 或其他不支援的系統執行**：立即說明不支援並停止，不做任何變更。
- **Claude Code 尚未登入**：不視為失敗，在摘要提示登入。

## Requirements *(mandatory)*

### Functional Requirements

**授權**

- **FR-001**: repo 根目錄 MUST 有 `LICENSE`，內容為未經改動的 Apache-2.0 全文。
- **FR-002**: repo MUST 有第三方聲明，列出來自 Spec Kit 的路徑、上游來源、MIT 條款與原著作權聲明。
- **FR-003**: README MUST 有授權段落，連到 `LICENSE` 與第三方聲明。
- **FR-004**: 這個功能新增的檔案 MUST 全部列入 `.repo-allowlist`，且 MUST 通過 commit 防護。

**一行指令設定**

- **FR-005**: MUST 分別提供 Linux 與 Windows 各一行可直接貼上的設定指令，並寫在 README 安裝段落的最前面。
- **FR-006**: 指令 MUST 檢查 uv、git、Claude Code，自動安裝缺少的工具，且 MUST NOT 更動已存在的工具。
- **FR-007**: 工具 MUST 來自其官方或作業系統提供的來源，且全程以加密連線下載。
- **FR-008**: 指令 MUST 取得 repo 到預設位置，使用者 MUST 能指定其他位置。
- **FR-009**: 指令 MUST 使用現有的部署功能部署設定，並沿用其備份、衝突處理與狀態回報行為。
- **FR-010**: 重複執行 MUST 得到相同結果；沒有更新時 MUST NOT 產生任何變更。
- **FR-011**: 更新 clone 時 MUST 只接受不會遺失本機改動的更新；否則 MUST 停止並說明。
- **FR-012**: 結束時 MUST 顯示摘要，列出已安裝的工具、repo 位置、部署結果與尚待使用者處理的事項；失敗時 MUST 指出失敗的步驟與處理方式，並以非零結束碼結束。
- **FR-013**: 指令 MUST 在不支援的作業系統上於任何變更前停止。

**開發設定**

- **FR-014**: 開發設定 MUST 只在使用者明確加上選項時執行。
- **FR-015**: 開發設定 MUST 把 email 寫入該 clone 的本機設定，MUST NOT 寫入全域設定或任何入庫檔案，且 MUST 拒絕不是 GitHub noreply 格式的地址。
- **FR-016**: 開發設定 MUST 使用既有的 commit 防護安裝功能，且 MUST NOT 覆蓋其他工具的 hook。
- **FR-017**: 開發選項與 email MUST 能透過同一行指令傳入。
- **FR-018**: 本機識別清單不存在時，開發設定 MUST 在摘要提示如何建立，並說明缺少時 push 不會通過；MUST NOT 自動產生清單內容。

**解除與驗證**

- **FR-019**: MUST 提供單一解除指令，還原 `~/.claude/`；曾做開發設定時 MUST 同時移除 commit 防護並還原提交身分。
- **FR-020**: 解除 MUST NOT 移除自動安裝的工具與 clone，且 MUST 在摘要列出它們與移除方式。
- **FR-021**: 設定與解除 MUST 有自動化測試；測試 MUST 能改用本機來源與隔離環境，不需連線到公開 repo，也不碰使用者真正的 `~/.claude/`。
- **FR-022**: README MUST 更新安裝段落，以一行指令取代手動步驟，依實際驗收結果更新「目前狀態」，並移除「已知限制」中授權尚未決定的說明。

### Key Entities

- **設定指令**：使用者貼上的一行指令，Linux 與 Windows 各一，接受位置與開發選項。
- **工具清單**：uv、git、Claude Code，各有檢查方式與各作業系統的安裝來源。
- **設定紀錄**：這次安裝了哪些工具、clone 位置、開發設定前的提交身分；存在本機、不入庫，供解除時使用。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 在乾淨的 Linux 與 Windows 環境，除了貼上指令與回應作業系統的權限提示，不需要其他操作就能完成設定。
- **SC-002**: 網路正常時，從貼上指令到看到完成摘要在 10 分鐘內。
- **SC-003**: 完成設定後連續再執行兩次，`~/.claude/` 與 clone 都沒有任何變更。
- **SC-004**: 設定後解除，`~/.claude/` 與設定前的逐檔比對 100% 相同。
- **SC-005**: 每個失敗情境（Edge Cases 所列）都顯示失敗步驟與處理方式，並回傳非零結束碼，自動化測試涵蓋率 100%。
- **SC-006**: repo 公開後，常見的授權偵測工具能辨識為 Apache-2.0，且第三方聲明涵蓋 100% 來自 Spec Kit 的路徑。
- **SC-007**: 完整檢查（`specs/001-repo-commit-guard`）對這個功能新增的全部檔案回報通過。

## Assumptions

- 著作權人使用 git 名稱 `flysangel`，年份 2026，不放 email。
- Spec Kit 的 MIT 條款以上游 `github/spec-kit` 的 `LICENSE` 為準（v1.2.6 已確認為 MIT）。
- 預設 clone 位置為家目錄下的 `claude-dotfiles`。
- 正式網址是 `github.com/flysangel/claude-dotfiles`，目前為私有；一行指令從預設分支 `main` 取得腳本。
- Linux 機器已有 `curl` 或 `wget` 其中之一，否則一行指令本身無法執行；README 提供兩種寫法。
- 自動安裝 git 只支援主流 Linux 發行版的套件管理工具與 Windows 內建的套件管理工具。
- 登入 Claude Code 屬於使用者自己的操作，不在自動化範圍內；這個功能也不處理 `~/.claude/settings.json`。
- 只提供遠端一行指令，不另設 clone 後的入口；已有 clone 的機器重新貼同一行即可。

## Dependencies

- **`specs/001-repo-commit-guard` 必須先完成才能公開**：一行指令要能匿名取得 repo，必須等 repo 公開。001 的程式已完成，私有 repo 也已建立，還剩 T029、T030（Windows 驗收與最終檢查）。公開前只能用 FR-021 的本機來源驗收；真實遠端指令要在公開後各作業系統再驗一次，才算完成。
- 開發設定對接 001 的 `tools/repo_guard.py --install-hook`。
- Windows 上的部署尚未驗收（見 README），這個功能的 Windows 驗收也會同時涵蓋它。
