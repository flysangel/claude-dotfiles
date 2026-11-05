# Feature Specification: 個人化 SDD 工具組

**Feature Branch**: `002-personal-sdd-toolkit`

**Created**: 2026-11-05

**Status**: Draft

**Input**: User description: "我這個專案要設計的是我個人化的 claude.md 還有我常用的 skill ，同時還有設計如何將 speckit 納入這個專案讓我以後新專案都可以快速使用 speckit ，另外還要自訂 skill，我目前訂定使用 sdd 並用 speckit 作為主要的方法，我希望透過一個 skill 讀取我計有專案導出 consitution、specify 至於 plan 則可以另外討論，還需要令一個 skill 類似 grillme 但可以討論出專案該使用什麼 consitution 與 specify"

## Clarifications

### Session 2026-11-05

- Q: 第一版的「常用 skill」納入哪些？ → A: 只做「專案導出」與「追問討論」兩個新 skill，其他之後逐項加入。
- Q: 導出 skill 的產出怎麼切？ → A: 一份 constitution 草稿加候選功能清單，由維護者選擇要導出哪些功能，每個功能一份 spec。
- Q: 新專案使用哪個版本的 Spec Kit？ → A: 一律使用最新版。
- Q: 同一個專案會在兩個作業系統上開發嗎？ → A: 通常只在一個系統，依導入當下的作業系統選擇腳本。
- Q: 「每次異動後在分支上 commit」要套用到所有專案嗎？ → A: 所有專案都套用，但不自動 push。
- Q: skill 產生的文件用什麼語言？ → A: 跟隨專案既有文件的語言；沒有或無法判斷時用繁體中文，規範詞保留英文。
- Q: 追問討論涉及多個功能時要產生幾份 spec？ → A: 討論到每個功能都有結論，每個功能各一份 spec。
- Q: 產生多份 spec 後如何接續 plan？ → A: 依功能相依順序產生，結束時列出清單，並將目前功能指向第一份。
- Q: 追問討論中斷後要能接續嗎？ → A: 每個決定都存入本機進度檔，下次接續，完成後刪除。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 在任何機器上部署個人化設定 (Priority: P1)

維護者在一台 Windows 或 Linux 機器上執行一次部署，個人化的 CLAUDE.md 與自訂 skill 就在該機器的所有專案生效。機器上原有的設定會先備份，也能完整還原。

**Why this priority**: 這是其他功能的基礎。沒有部署，CLAUDE.md 與 skill 只能留在這個 repo，無法用在其他專案。

**Independent Test**: 在一個已有 CLAUDE.md 的測試環境部署，確認新設定在另一個專案生效、舊內容有備份；解除部署後確認環境與部署前相同。

**Acceptance Scenarios**:

1. **Given** 機器上已有個人 CLAUDE.md，**When** 部署，**Then** 舊內容先備份，新內容生效。
2. **Given** 已部署過，**When** 再次部署，**Then** 結果相同，也不會產生多餘的備份或重複內容。
3. **Given** 已部署，**When** 解除部署，**Then** 機器回到部署前的狀態。
4. **Given** 機器上有非本 repo 管理的 skill，**When** 部署或解除部署，**Then** 這些 skill 完全不受影響。
5. **Given** 新對話開始，**When** 維護者與 Claude 互動，**Then** Claude 的行為符合 CLAUDE.md 寫明的預期行為。

---

### User Story 2 - 新專案快速導入 Spec Kit (Priority: P1)

維護者在新專案或既有專案內，用一個步驟導入最新版 Spec Kit，不必記住初始化選項。導入後依專案作業系統可直接使用，並提示下一步該用哪個 skill。

**Why this priority**: 維護者已決定以 SDD 與 Spec Kit 為主要方法，每個新專案都要做這一步，兩個自訂 skill 也依賴它。

**Independent Test**: 分別在 Windows 與 Linux 的空資料夾導入，確認 Spec Kit 指令可用，且產生的腳本符合該作業系統。

**Acceptance Scenarios**:

1. **Given** 空的專案資料夾，**When** 導入，**Then** Spec Kit 可直接使用，資料夾已是沒有 commit 的 git repo，並提示下一步使用追問討論 skill。
2. **Given** 已有程式碼但未導入 Spec Kit 的專案，**When** 導入，**Then** 既有檔案不被覆蓋，並提示下一步使用專案導出 skill。
3. **Given** 專案已導入且已有 constitution 或 spec，**When** 再次導入，**Then** 不會覆蓋這些內容，也不會自動升級。
4. **Given** 必要工具缺少或無法取得最新版，**When** 導入，**Then** 清楚說明原因與處理方式，專案不留下不完整的結果。
5. **Given** 導入完成，**When** 查看結果，**Then** 能得知這次安裝的 Spec Kit 版本。

---

### User Story 3 - 從既有專案導出 constitution 與 spec (Priority: P2)

維護者對一個已有程式碼的專案執行導出 skill。skill 讀取專案後，提出一份 constitution 草稿與候選功能清單；維護者選擇要導出的功能，每個功能得到一份 spec。所有推論都標明依據，流程止於 spec，不進入 plan。

**Why this priority**: 既有專案要改用 SDD 時，從零撰寫 constitution 與 spec 的成本很高，這個 skill 可以省下最多人工。

**Independent Test**: 對一個有程式碼與文件的範例專案執行，確認草稿每條原則都有依據、功能清單可選擇，且確認前目標專案沒有任何檔案被修改。

**Acceptance Scenarios**:

1. **Given** 已導入 Spec Kit 的既有專案，**When** 執行導出，**Then** 得到 constitution 草稿與候選功能清單，每條原則與每個功能都標明依據的檔案。
2. **Given** 候選功能清單，**When** 維護者選擇其中兩項，**Then** 只產生這兩項的 spec，每項一份。
3. **Given** 草稿尚未確認，**When** 檢查目標專案，**Then** 沒有任何檔案被修改。
4. **Given** 專案已有 constitution，**When** 執行導出，**Then** 只提出差異供確認，不會直接覆蓋。
5. **Given** 某項內容無法從專案判斷，**When** 產生草稿，**Then** 標為待確認，不會當成事實寫入。
6. **Given** 專案內含憑證或 token，**When** 產生草稿，**Then** 草稿與 spec 都不包含這些值。
7. **Given** spec 已產生，**When** 流程結束，**Then** skill 停止，不會自動進入 plan。
8. **Given** 選定多個功能，**When** 產生 spec，**Then** 依相依順序編號，結束時列出清單與建議順序，且目前功能指向第一份。

---

### User Story 4 - 透過追問討論出 constitution 與 spec (Priority: P2)

維護者對一個新專案或方向未定的專案執行追問討論 skill。skill 一次問一個問題，每題附上建議答案與理由，持續追問直到決策都有結論，再把結果交給 Spec Kit 寫成 constitution 與 spec。

**Why this priority**: 維護者不確定 constitution 該怎麼設計時，最需要的是有人逼出隱藏的決策，這也是這份 repo 的起點。

**Independent Test**: 用一句模糊的專案描述開始討論，確認每次只問一題、每題都有建議，結束時的決策摘要足以產生沒有待釐清標記的 constitution 與 spec。

**Acceptance Scenarios**:

1. **Given** 一句模糊的專案描述，**When** 開始討論，**Then** 每次只問一個問題，並附上建議答案與理由。
2. **Given** 問題的答案可以從專案內容查到，**When** 討論進行，**Then** skill 自行查閱，不會詢問維護者。
3. **Given** 維護者的回答與先前決策矛盾，**When** 討論進行，**Then** skill 指出矛盾並要求取捨。
4. **Given** 維護者的回答含糊，**When** 討論進行，**Then** skill 追問到能判斷對錯為止。
5. **Given** 所有決策都有結論或已明確延後，**When** 維護者確認決策摘要，**Then** 才寫入 constitution，並為每個功能各寫入一份 spec。
6. **Given** 討論中途停止，**When** 維護者要求結束，**Then** 得到一份已決定與未決定事項的摘要，進度已保存，且不寫入 constitution 或 spec。
7. **Given** 討論碰到技術選型這類 plan 層級的問題，**When** 討論進行，**Then** 記錄為留給 plan，不在此決定。
8. **Given** 上次討論已中斷，**When** 再次執行，**Then** 列出已決定事項，並由維護者選擇接續或重新開始。
9. **Given** 討論已完成且文件已寫入，**When** 檢查專案，**Then** 進度檔已刪除。

---

### User Story 5 - 逐項加入新的常用 skill (Priority: P3)

維護者遇到實際需求或提出明確要求時，能把一個新 skill 加入此 repo，經過同樣的驗證後部署到所有機器。

**Why this priority**: 第一版只有少數 skill，但此 repo 的目的是持續累積個人常用 skill。

**Independent Test**: 依文件加入一個範例 skill，部署後確認它在其他專案可用，解除部署後確認它被移除。

**Acceptance Scenarios**:

1. **Given** 一個新 skill 與它解決的實際需求，**When** 維護者依流程加入，**Then** 重新部署後即可使用。
2. **Given** 新 skill 缺少觸發案例，**When** 執行驗證，**Then** 驗證不通過。

---

### Edge Cases

- **Spec Kit 最新版有不相容變更**：自訂 skill 找不到所依賴的 Spec Kit 功能時，MUST 明確回報並停止，不得產生殘缺結果。
- **專案內容太少**：導出 skill 無法提出足夠依據時，MUST 說明情況並建議改用追問討論 skill。
- **文件與程式碼矛盾**：導出 skill MUST 同時列出兩邊，交由維護者決定，不得自行選擇。
- **大型專案或 monorepo**：導出 skill 只列出候選功能，由維護者縮小範圍，不要求一次讀完全部內容。
- **第三方與產生的內容**：導出 skill MUST 排除相依套件與建置產物，不將其視為專案功能。
- **專案尚未導入 Spec Kit**：專案導出與追問討論 skill 都 MUST 提示先導入，不得自行寫入。
- **既有 CLAUDE.md 含個人內容**：部署 MUST 只備份，不得將其內容納入此 repo。
- **切換功能**：Spec Kit 的目前功能不會隨 git 分支切換，也不入庫；skill 結束時的清單 MUST 說明如何切換。
- **進度檔過期**：接續時若專案已有變更，MUST 提示維護者，由其決定是否沿用。
- **部署中斷**：MUST 能再次執行而完成部署，或透過解除部署回到原狀。
- **機器專屬內容**：個人識別或機器專屬的內容 MUST 放在不入庫的本機位置，且部署後仍然生效。

## Requirements *(mandatory)*

### Functional Requirements

**個人化 CLAUDE.md 與部署**

- **FR-001**: 此 repo MUST 提供一份適用於所有專案的個人化 CLAUDE.md，只包含行為偏好與 SDD 工作方式，每條規則 MUST 寫明可觀察的預期行為。
- **FR-002**: CLAUDE.md MUST 少於 200 行，用標題與條列分組，規則之間 MUST NOT 互相矛盾，MUST NOT 放能從程式碼得知的內容，MUST NOT 包含機密、個資或機器專屬內容。
- **FR-003**: 維護者 MUST 能以一個指令將 CLAUDE.md 與此 repo 管理的 skill 部署到目前機器，重複執行結果相同。
- **FR-004**: 部署覆蓋既有檔案前 MUST 備份，MUST 能解除部署並還原，MUST NOT 影響非此 repo 管理的內容。
- **FR-005**: 維護者 MUST 能查出目前機器的部署狀態，以及本機內容是否與 repo 不同。

**Spec Kit 導入**

- **FR-006**: 維護者 MUST 能在任何專案以一個步驟導入 Spec Kit，不需要提供初始化選項。
- **FR-007**: 導入 MUST 使用當下的最新穩定版 Spec Kit，排除預發布版，並回報實際安裝的版本。
- **FR-008**: 導入 MUST 依導入當下的作業系統，設定可在該系統上運作的腳本類型，並在完成時提示專案換到另一個作業系統需要對應的 shell。
- **FR-009**: 導入 MUST NOT 覆蓋專案既有內容；在已導入的專案上重複執行 MUST NOT 改動任何內容，也 MUST NOT 自動升級。
- **FR-010**: 導入失敗時 MUST 說明原因與處理方式，MUST NOT 留下不完整的結果。
- **FR-011**: 導入完成後 MUST 依專案是否已有內容，建議下一步使用專案導出或追問討論 skill。
- **FR-012**: 維護者 MUST 能移除導入所建立且未修改的檔案，包含未修改的 constitution 範本，讓專案回到導入前的狀態；已修改的檔案 MUST 保留並回報，除非維護者明確要求一併移除；spec MUST NOT 被移除。
- **FR-033**: 目標資料夾不在 git repo 內時，導入成功後 MUST 建立 git repo，且 MUST NOT 自動 commit；移除導入時 MUST NOT 刪除 `.git`。

**專案導出 skill**

- **FR-013**: skill MUST 讀取既有專案，提出一份 constitution 草稿與候選功能清單，並讓維護者選擇要導出的功能。
- **FR-014**: skill MUST 為每個選定的功能各產生一份 spec。
- **FR-015**: 每條原則與每個功能 MUST 標明依據的檔案；無法判斷的內容 MUST 標為待確認。
- **FR-016**: skill MUST 區分「專案已經這樣做」與「專案應該這樣做」，後者 MUST 由維護者確認才能成為原則。
- **FR-017**: 維護者確認前，skill MUST NOT 修改目標專案；已有 constitution 或 spec 時 MUST 提出差異，MUST NOT 直接覆蓋。
- **FR-018**: 產出 MUST NOT 包含專案內的機密值。

**追問討論 skill**

- **FR-019**: skill MUST 一次只問一個問題，每題 MUST 附上建議答案與理由。
- **FR-020**: 能從專案內容查到的答案，skill MUST 自行查閱，MUST NOT 詢問維護者。
- **FR-021**: skill MUST 追問含糊的回答，並指出與先前決策矛盾之處。
- **FR-022**: 討論範圍 MUST 涵蓋 constitution 與 spec 所需的決策；技術選型等 plan 層級的問題 MUST 記錄為留給 plan。
- **FR-023**: 討論 MUST 涵蓋專案的每個功能，持續到所有決策都有結論或已明確延後，維護者也 MUST 能隨時結束並取得摘要。
- **FR-024**: 只有在維護者確認決策摘要後，skill 才能寫入 constitution，並為每個功能各寫入一份 spec。
- **FR-032**: 追問討論 MUST 在每個決定後保存進度，再次執行時 MUST 讓維護者選擇接續或重新開始，完成後 MUST 刪除進度。進度 MUST 只存於本機、不入庫，且不記錄機密值。

**共通要求**

- **FR-025**: 專案導出與追問討論 skill MUST 透過 Spec Kit 既有的 constitution 與 specify 流程產生文件，讓產出符合 Spec Kit 的格式與規則。
- **FR-026**: 專案導出與追問討論 skill MUST 止於 spec，MUST NOT 進入 plan。
- **FR-027**: 每個 skill MUST 有觸發案例，涵蓋應觸發與不應觸發的提示；只能手動執行的 skill 改為確認不會自動觸發。
- **FR-028**: 所有功能 MUST 在 Windows 與 Linux 上行為一致。
- **FR-029**: 此 repo MUST 提供加入新 skill 的流程，加入時 MUST 指出該 skill 的需求來源：實際遇到的需求或維護者的明確要求。
- **FR-030**: 專案導出與追問討論 skill 產生的文件 MUST 使用專案既有文件的語言；沒有既有文件或無法判斷時 MUST 使用繁體中文，MUST、SHOULD 等規範詞保留英文。
- **FR-031**: 產生多份 spec 時，專案導出與追問討論 skill MUST 依功能相依順序產生，結束時 MUST 列出清單與建議順序，並將目前功能指向這批的第一份。

### Key Entities

- **個人化 CLAUDE.md**: 適用於所有專案的行為偏好，由此 repo 管理並部署到各機器。
- **自訂 skill**: 由此 repo 管理的按需流程，第一版有專案導出、追問討論，以及只能手動執行的 Spec Kit 導入。
- **導入紀錄**: 記錄導入的 Spec Kit 版本與建立的檔案，作為移除的依據，隨目標專案入庫。
- **部署紀錄**: 記錄此 repo 部署了哪些內容與備份位置，作為查詢狀態與還原的依據，只存在本機。
- **Constitution 草稿**: 尚未確認的原則，每條都附依據，或標為待確認。
- **候選功能清單**: 從專案辨識出的功能，每項附依據，供維護者選擇。
- **決策摘要**: 追問討論的結果，列出已決定、已延後與留給 plan 的事項。
- **討論進度**: 尚未完成的決策摘要，存於本機，用於接續討論。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 維護者能在 5 分鐘內，於一台新的 Windows 或 Linux 機器完成部署並確認生效。
- **SC-002**: 解除部署後，機器上受影響的檔案與部署前 100% 相同。
- **SC-003**: 網路正常時，新專案能在 2 分鐘內完成 Spec Kit 導入並開始下一步。
- **SC-004**: 導出草稿中 100% 的原則與候選功能都有依據或標為待確認。
- **SC-005**: 維護者確認導出的 constitution 時，被整條改寫或刪除的原則少於一半。
- **SC-006**: 追問討論完成後產生的 constitution 與 spec，待釐清標記為 0。
- **SC-007**: 專案導出與追問討論 skill 的觸發案例 100% 符合預期，應觸發的會觸發，不應觸發的不會觸發。
- **SC-008**: 範例專案的假憑證出現在導出產出中的次數為 0。
- **SC-009**: 加入一個新 skill 並部署到機器，只需一次修改與一次部署。

## Assumptions

- **使用者**：只有一位維護者，使用自己的 Windows 與 Linux 機器；macOS 不在範圍內。
- **第一版 skill 範圍**：常用 skill 只包含專案導出與追問討論；Spec Kit 導入另有一個只能手動執行的 skill 作為入口；Orca 相關 skill 由 Orca 管理，不納管。
- **CLAUDE.md 初始內容**：來自維護者已表達的偏好：以繁體中文回覆、提問使用互動式選項、每次異動後在分支上 commit（適用所有專案，不自動 push）、以 SDD 與 Spec Kit 為主要工作方式。維護者已確認這些內容。
- **Spec Kit 來源**：維護者選擇一律使用最新版。不同時間的新專案可能拿到不同版本，這與憲章原則 IV 不符，例外記錄在 plan 的 Complexity Tracking；在同一專案上重複執行不改變結果。
- **前置工具**：機器上需能取得 Spec Kit 的官方安裝工具，部署或導入時若缺少則提示處理方式。
- **與 001 的關係**：完整入庫防護由 `001-repo-commit-guard` 處理，此 repo 公開前必須完成。在那之前，本功能先建立最小白名單與 git pre-commit 檢查，以符合憲章原則 I；這項檢查每個 clone 都要安裝一次，也能被 `--no-verify` 略過。
- **Plan 不在範圍內**：維護者表示 plan 階段另外討論，本功能的 skill 不產生 plan。
- **Settings 與 hook 不在範圍內**：個人 settings 與 hook 的納管留待後續功能。
