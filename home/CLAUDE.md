# 個人工作偏好

## 溝通

- 以繁體中文回覆；指令、程式碼識別字與專有名詞保留原文。
  預期：我用英文提問時，回覆仍是繁體中文。
- 需要我做決定時，使用互動式提問工具 AskUserQuestion，不要用純文字提問。
  預期：每個待決定事項都以選項呈現，並標出你建議的選項。

## Git

- 每完成一項異動就 commit，不等我要求。
  預期：回合結束時，你改過的檔案沒有未提交的內容。
- 不直接 commit 到 `main`；目前在 `main` 上時先開分支。
  預期：`git log main` 不會多出你直接提交的 commit。
- 只在我明確要求時才 push。
  預期：commit 後遠端沒有變化。

## 規格驅動開發

新功能以 Spec Kit 依序進行 spec、plan、tasks、implement；修正錯字這類不改變行為的小改動除外。

- 專案還沒有 `.specify/` 時，請我執行 `/sdd-init`。
  預期：你不會手動建立 Spec Kit 的檔案。
- 既有專案要補 constitution 或 spec 時，使用 `sdd-derive`。
  預期：先提出附依據的草稿，我確認後才寫入。
- 方向未定，或要討論該用什麼 constitution 與 spec 時，使用 `sdd-grill`。
  預期：一次只問一題，並附上你的建議。
