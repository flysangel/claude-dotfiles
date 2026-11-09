# Contract: Skill 行為

## 共通前置檢查（`sdd-derive`、`sdd-grill`）

開始前確認以下項目，任一不符就回報並停止，不寫入任何內容：

- `.specify/` 存在；否則提示先執行 `/sdd-init`。
- 專案內有 `speckit-constitution` 與 `speckit-specify` skill，且未設定 `disable-model-invocation: true`；否則回報 Spec Kit 可能有不相容的變更。

## `sdd-derive`

**觸發**：要從既有專案導出 constitution 或 spec。

| 步驟 | 行為 |
|---|---|
| 1. 讀取 | 文件、設定、測試與程式結構；排除相依套件與建置產物；不把機密值帶入對話 |
| 2. 提案 | 提出 constitution 草稿與候選功能清單，每項附依據；大型專案先請維護者縮小範圍 |
| 3. 確認 | 維護者確認原則並選擇功能，也可選擇只要 spec；文件與程式碼矛盾時列出兩邊，由維護者決定 |
| 4. 產生 | 呼叫 `speckit-constitution`（只要 spec 時跳過），再依相依順序為每個選定功能呼叫一次 `speckit-specify` |
| 5. 結束 | 依「多份 spec 的接續」收尾後停止，不進入 plan |

例外：
- 專案內容不足以推論時，說明原因並建議改用 `sdd-grill`。
- 已有 constitution 或 spec 時，提出差異，確認後才修改。

**不觸發**：一般程式碼問題、單純詢問 Spec Kit 用法、已經指定要跑 `speckit-*` 的情況。

## `sdd-grill`

**觸發**：要討論或決定專案該用什麼 constitution 與 spec，或方向未定。

| 規則 | 行為 |
|---|---|
| 提問 | 一次一題，附建議答案與理由 |
| 查證 | 能從專案查到的答案自行查閱 |
| 追問 | 回答含糊時繼續問；與先前決策矛盾時要求取捨 |
| 範圍 | 只討論 constitution 與 spec，涵蓋每個功能；技術選型記為留給 plan |
| 結束 | 全部決策有結論或已延後後呈現決策摘要，確認才呼叫 `speckit-constitution`，再依相依順序為每個功能呼叫一次 `speckit-specify`，依「多份 spec 的接續」收尾並刪除進度檔 |
| 進度 | 每個決定後更新 `.specify/sdd-grill-progress.md`；建立時將其加入 `.specify/.gitignore`；不記錄機密值 |
| 中途停止 | 提供已決定與未決定事項的摘要，不寫入 constitution 或 spec |
| 接續 | 進度檔存在時列出已決定事項，由維護者選擇接續或重新開始；專案已有變更時先提示 |

**不觸發**：只想要一次性意見、已經有明確規格要實作、要討論技術實作細節。

## `sdd-init`

設定 `disable-model-invocation: true`，只能手動執行。行為見 [sdd-init.md](sdd-init.md)。

## 多份 spec 的接續（`sdd-derive`、`sdd-grill`）

1. 依功能相依順序呼叫 `speckit-specify`，讓編號等於建議的施工順序。
2. 全部完成後，把 `.specify/feature.json` 的 `feature_directory` 設為這批的第一份，檔案不存在就建立；專案的 `speckit-specify` 沒有提到 `feature_directory` 時不寫入，改為回報。
3. 列出每份 spec、相依關係，並說明下一步是 `/speckit-plan`，以及如何改 `feature.json` 切換功能。

## 文件語言（`sdd-derive`、`sdd-grill`）

使用專案既有文件的語言；沒有或無法判斷時用繁體中文，規範詞保留英文。

## 驗收格式

每個 skill 在 `tests/skills/<skill>/` 需要：

- `triggers.json`：`should_trigger` 與 `should_not_trigger` 提示，`sdd-init` 改為確認不會自動觸發。
- `scenarios.md`：對應 spec 驗收情境的操作與預期結果。
