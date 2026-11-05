# claude-dotfiles Constitution

## Core Principles

### I. 機密與個資不入庫（NON-NEGOTIABLE）

本 repo 公開，任何進入 git 歷史的內容都視為已公開。

- 憑證、token、對話紀錄與 session 資料 MUST NOT 進入 git。
- email、內部路徑等個人資訊 MUST NOT 進入 git，包含範例與測試資料。
- 納管範圍 MUST 使用白名單：只有明確列入的檔案才能進入 repo，MUST NOT 納管整個 `~/.claude/`。
- 機密一旦進入 git 歷史，MUST 視為已外洩並立即更換，只刪除檔案不算修復。

理由：`~/.claude/` 同時存在 `.credentials.json`、`history.jsonl` 這類檔案，黑名單一漏就會公開。

### II. 機制分層

每項客製化 MUST 放在符合其性質的機制，plan MUST 說明選擇理由：

| 性質 | 機制 |
|---|---|
| 必須強制執行 | hook 或 settings |
| 每次都適用的偏好 | CLAUDE.md |
| 按需使用的流程 | skill |
| 需要隔離 context 的工作 | subagent |

必須強制執行的規則 MUST NOT 只寫在 CLAUDE.md。

理由：CLAUDE.md 依賴 Claude 自行遵守，只有 hook 與 settings 由工具強制執行。

### III. Context 精簡

- 此 repo 產出的每個 CLAUDE.md MUST 少於 200 行；達到上限時 MUST 先移除或搬到其他機制，才能新增內容。
- 用 `@path` 拆分檔案 MUST NOT 視為精簡，因為匯入的檔案會一起載入 context。
- 只在部分情況需要的內容 MUST 移到 skill 或限定路徑的 rules。
- CLAUDE.md MUST NOT 放能從程式碼得知的內容（目錄結構、相依清單、架構總覽），只保留陷阱、理由與不同於工具預設的慣例。
- 常駐內容（CLAUDE.md、skill 描述）的每一行 MUST 能說明存在理由；說不出理由的內容 MUST 移除。
- 新增內容 MUST 來自實際遇到的需求或維護者的明確要求，plan MUST 指出來源；MUST NOT 為假設的未來需求預先設計。

理由：常駐內容在每次對話都佔用 context，也會稀釋其他規則的效果。200 行與上述規則依據
[官方 CLAUDE.md 建議](https://code.claude.com/docs/en/memory)。

### IV. 安裝可重現、可還原、跨平台

- 安裝 MUST 只需一個指令，且重複執行的結果 MUST 相同。
- 覆蓋既有檔案前 MUST 備份。
- MUST 提供解除安裝方式，並還原安裝前的狀態。
- 機器專屬的設定與路徑 MUST 與共用設定分離，且機器專屬部分 MUST NOT 入庫。
- 入庫內容 MUST NOT 寫死絕對路徑。
- 支援的作業系統為 Windows 與 Linux；macOS 不在支援範圍。
- 安裝與 hook 腳本 MUST 能在 Windows 與 Linux 上運作，MUST NOT 只依賴僅存在於單一作業系統的 shell 或工具。

理由：同一份設定要在多台不同系統的機器上運作，且不能破壞機器上原有的設定。

### V. 可驗證

每項產出 MUST 附上驗證方式，未附驗證方式的項目不算完成：

- hook MUST 有自動化測試，涵蓋觸發與不觸發的情況。
- skill MUST 有觸發案例，涵蓋應觸發與不應觸發的提示。
- CLAUDE.md 規則 MUST 具體到可以驗證，並寫明可觀察的預期行為，例如「commit 前執行 `npm test`」，而不是「測試你的變更」。
- CLAUDE.md MUST 用標題與條列分組，規則之間 MUST NOT 互相矛盾。
- 修改 CLAUDE.md、rules 或 skill 後 SHOULD 執行 `/doctor prompt-audit`，檢查過時或衝突的內容。
- 安裝與解除安裝 MUST 有驗證步驟。

理由：設定類改動常在沒有錯誤訊息的情況下失效，必須有可檢查的依據。

## 範圍與邊界

本文件只規範如何開發此 repo，MUST NOT 描述 Claude 的行為偏好：

- 跨功能且長期不變的開發規則：放在本文件。
- 個別功能的需求：放在 feature spec。
- Claude 的行為偏好：放在 CLAUDE.md，它是此 repo 的產出物。

## 開發流程與品質關卡

功能開發 MUST 依序經過 spec、plan、tasks、implement。plan 的 Constitution Check MUST 逐條確認：

| 原則 | 關卡問題 |
|---|---|
| I | 新增的入庫檔案都在白名單內，且不含機密與個資嗎？ |
| II | 每項客製化都說明了為何選擇該機制嗎？ |
| III | 指出需求來源了嗎？每個 CLAUDE.md 少於 200 行，且不含能從程式碼得知的內容嗎？ |
| IV | 安裝可重複執行、可還原，且能在 Windows 與 Linux 上運作嗎？ |
| V | 每項產出都有驗證方式嗎？CLAUDE.md 規則具體可驗證且沒有矛盾嗎？ |

commit 前 MUST 檢查待提交內容符合原則 I。

## Governance

本文件優先於此 repo 的其他開發慣例。此為個人專案，修改不需審核流程，但 MUST 遵守以下規定：

- 修改時 MUST 更新版本與 Last Amended 日期，並在 commit message 寫明原因。
- 版本採語意化規則：
  - MAJOR：移除原則，或重新定義原則使其與舊版不相容。
  - MINOR：新增原則或章節，或實質擴充規範。
  - PATCH：釐清說明、修正文字，不改變規範含義。
- 違反原則 II 至 V 時 MUST 在 plan 的 Complexity Tracking 記錄理由；原則 I 不得豁免。

**Version**: 1.3.0 | **Ratified**: 2026-11-05 | **Last Amended**: 2026-11-06
