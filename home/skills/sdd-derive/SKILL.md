---
name: sdd-derive
description: Derive a Spec Kit constitution and per-feature specs from an existing codebase. Use when the user wants to adopt spec-driven development on a project that already has code, or asks to extract, derive, or backfill a constitution or specs (導出、補上 constitution 或 spec). Not for general code questions, how-to questions about Spec Kit, or new projects with no code.
---

# 從既有專案導出 constitution 與 spec

讀取專案後提出有依據的草稿，由維護者確認，再交給 Spec Kit 產生文件。流程止於 spec，不進入 plan。

**維護者確認前，不得修改目標專案的任何檔案。**

## 1. 前置檢查

任一項不符就回報並停止：

- 專案有 `.specify/`。沒有就請維護者先執行 `/sdd-init`。
- `.claude/skills/speckit-constitution/SKILL.md` 與 `.claude/skills/speckit-specify/SKILL.md` 都存在，且沒有 `disable-model-invocation: true`。不符就說明 Spec Kit 可能有不相容的變更，不要自行寫出這些文件。

## 2. 讀取專案

- 讀文件、設定、測試與程式結構。
- 排除相依套件與建置產物，例如 `vendor/`、`node_modules/`、`dist/`。它們不是這個專案的功能。
- 不開啟 `.env`、金鑰與憑證檔；其他檔案裡出現機密時，只記錄位置。**機密值不得出現在對話、草稿或產出中。**
- 專案很大或是 monorepo 時，先列出主要區塊，請維護者縮小範圍，不要一次讀完。
- 內容太少而無法提出依據時，說明原因，建議改用 `sdd-grill`，然後停止。

## 3. 提出草稿

**Constitution 草稿**，每條原則標明：

- 類型：`已經這樣做`（專案目前的做法）或 `應該這樣做`（你的建議，須維護者同意才算數）
- 依據：專案內的檔案路徑
- 狀態：`有依據` 或 `待確認`。無法判斷就標 `待確認`，不要寫成事實。

**候選功能清單**，每個功能附使用者角度的描述、依據的檔案，以及它依賴哪些功能。

文件與程式碼矛盾時，把兩邊都列出來，不要自行選擇。

專案已有 constitution 或 spec 時，只提出差異，不要準備整份覆蓋。

## 4. 確認

請維護者確認原則、解決矛盾與待確認項目，並選擇要導出的功能。全部有結論前不要進入下一步。

## 5. 產生文件

文件使用專案既有文件的語言；沒有或無法判斷時用繁體中文，MUST、SHOULD 等規範詞保留英文。把語言要求寫進傳給 Spec Kit 的內容。

1. 用 Skill 工具呼叫 `speckit-constitution`，傳入確認後的原則。
2. 依功能相依順序，為每個選定的功能各呼叫一次 `speckit-specify`，傳入功能描述與確認過的決定。被依賴的功能排在前面，讓編號等於建議的施工順序。

無法呼叫這些 skill 時，回報並停止，不要自行寫出文件。

## 6. 收尾

第 1 步只在產生多份 spec 時才做：

1. 確認 `.specify/feature.json` 存在且有 `feature_directory` 欄位，把它改成這批的第一份。檔案或欄位不存在時不要寫入，只回報。
2. 列出每份 spec 的路徑、相依關係與建議順序。
3. 說明下一步是 `/speckit-plan`，以及切換功能要改 `.specify/feature.json` 的 `feature_directory`，切換 git 分支不會跟著切換。

然後停止，不要執行 plan。
