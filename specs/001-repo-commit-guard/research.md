# Research: 公開 repo 入庫防護

驗證環境：Linux、git、gitleaks 8.30.1（2026-11-06）。**未在 Windows 上實測。**

## 1. 擴充或重寫

- **Decision**: 擴充 `tools/check_allowlist.py` 並改名為 `tools/repo_guard.py`。
- **Rationale**: 既有工具已涵蓋 FR-001、FR-002、FR-004 到 FR-009，實際 commit 也驗證過。工具範圍變大後，舊名稱不再貼切。
- **Alternatives**: 另寫一支會有兩份規則；保留舊名則名稱與用途不符。

## 2. 掃描引擎

- **Decision**: 工具用內建規則，不依賴外部掃描器。公開前的最終確認另外手動跑一次 gitleaks，作為獨立的第二意見。
- **Rationale**: 內建規則不需額外安裝，Windows 與 Linux 行為一致，也能處理 email、個人路徑與本機識別清單，這些 gitleaks 預設不涵蓋。但內建的憑證規則較少，公開是不可逆的操作，值得多一道檢查。這台機器已有 gitleaks。
- **Alternatives**: 把 gitleaks 列為必要工具，會多一個兩邊都要安裝的前置條件，也解決不了個資比對。

## 3. 檢查 commit 訊息

- **Decision**: 新增 `commit-msg` hook，呼叫 `repo_guard.py --commit-msg <檔案>`。內容規則與檔案相同。
- **Rationale**: `pre-commit` 執行時訊息還不存在。Git 會把訊息檔路徑傳給 `commit-msg`。依程式碼，帳號層 dispatch 會依 hook 名稱轉交，但 `commit-msg` 還沒實測，實作時要確認。

## 4. 誤判例外

- **Decision**: 存在 `.repo-guard-exceptions.json`，每筆是 `path`、`kind`、`line_sha256`、`reason`。`line_sha256` 是該行內容的雜湊值，違規訊息會顯示它，方便複製。
- **Rationale**: 行號會隨編輯變動，整個類型或路徑又違反 FR-012。綁定該行內容後，行一改例外就失效，要重新確認。只存雜湊值，所以例外本身不含機密原文。
- **取捨**: 檔案類例外（二進位檔）沒有行內容，改用整個檔案的雜湊值。
- **Alternatives**: 行號太脆弱；gitleaks 式的註解標記要改動被檢查的檔案。

雜湊低熵內容理論上可以暴力還原，例外只該用於誤判，不是真機密，因此可以接受。真機密依憲章原則 I 視為外洩並更換。

## 5. 本機識別清單

- **Decision**: 存在 `~/.config/claude-dotfiles/identity.txt`，每行一筆，不分大小寫比對；可用環境變數 `REPO_GUARD_IDENTITY_FILE` 覆寫。不存在或沒有內容時，commit 檢查只提醒，`--history` 不通過，避免公開前誤以為比對過。作者與提交者名稱也會比對。
- **Rationale**: 真實姓名、私人主機名稱無法靠格式辨識。放在 home 下，repo 內就不會有副本。Windows 與 Linux 都適用。
- **輸出**: 只報「個人識別資訊」，不顯示比對到的內容。

## 6. 完整歷史檢查

- **Decision**: `--history` 掃描 `git rev-list --all` 的每個 commit：作者、提交者、訊息，以及該 commit 引入的每個檔案版本。同一份內容只掃一次。
- **Rationale**: 刪除過的機密仍在歷史裡，這正是 FR-014 要抓的。白名單與例外都以目前版本為準，例外靠內容雜湊比對，所以對舊版本同樣有效。
- **效能**: 每次 push 都會跑，實作時要量測；同一份內容只掃一次，repo 規模也小，預期不是問題。
- **限制**: 歷史檢查只回報，不修改歷史。只涵蓋 refs 可達的 commit，不含 reflog，後者也不會被 push。

## 7. 啟用狀態

- **Decision**: `--status` 回報 `enabled`、`not-installed` 或 `unverified`。設定了 `core.hooksPath` 且 hook 已裝時回報 `unverified`，因為工具無法確定共用目錄會不會轉交。
- **Rationale**: 這台機器就是這種情況。實測帳號層 dispatch 會轉交 `pre-commit`，但不能假設其他機器也會。回報 `enabled` 會給出錯誤的安全感。

## 8. 設定檢視

- **Decision**: 依鍵名與值分類，優先序為含機密、機器專屬、可共用、待判斷。只有明列的安全鍵（如 `theme`）且值不觸發規則才算可共用，其他一律待判斷。
- **Rationale**: FR-018 要求不確定時不得預設可共用。分類只列鍵路徑，不列值，鍵名本身也會先經過同一套識別規則。巢狀結構會往下找，並把整個頂層項目標為其中最嚴重的分類。目前這台機器的設定有 5 個頂層項目，`hooks` 與 `statusLine` 是主要內容。

## 9. 不在範圍內的防護

- **`--no-verify`**：commit hook 可被略過，由 `pre-push` hook 的 `--history` 補上。push 也能加 `--no-verify` 略過，這個缺口要靠 CI。
- **遠端防護**：CI 與伺服器端檢查留待設定 remote 後另外處理，如 spec 的 Assumptions 所述。設定 remote 後建議優先補上，因為公開後才發現的外洩無法收回。
