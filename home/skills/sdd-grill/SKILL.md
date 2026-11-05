---
name: sdd-grill
description: Question the user one decision at a time until a project's Spec Kit constitution and feature specs are fully decided, then generate them. Use when the user is unsure what constitution or specs a project needs, wants to be grilled or interviewed about it, or starts a project with an unclear direction (追問、釐清、討論 constitution 或 spec). Not for one-off opinions, technology choices, or implementing an existing spec.
---

# 透過追問決定 constitution 與 spec

逼出隱藏的決策，討論到每個功能都有結論，確認後交給 Spec Kit 產生文件。流程止於 spec，不進入 plan。

**維護者確認決策摘要前，不得寫入 constitution 或 spec。** 只有進度檔例外。

## 1. 前置檢查

任一項不符就回報並停止：

- 專案有 `.specify/`。沒有就請維護者先執行 `/sdd-init`。
- `.claude/skills/speckit-constitution/SKILL.md` 與 `.claude/skills/speckit-specify/SKILL.md` 都存在，且沒有 `disable-model-invocation: true`。不符就說明 Spec Kit 可能有不相容的變更，不要自行寫出這些文件。

## 2. 接續或開始

進度檔是 `.specify/sdd-grill-progress.md`。

存在時，先列出其中已決定的事項，問維護者要接續還是重新開始；重新開始就刪除它。若專案在上次討論後有變更，例如 `git log` 或檔案時間比進度檔新，先提示，由維護者決定是否沿用。

## 3. 追問

先讀專案現有內容，再開始問。

- **一次只問一題。** 需要做決定時，使用互動式提問工具 AskUserQuestion；工具不能用時改用文字。
- **每題都附建議答案與理由**，建議放在第一個。
- **能從專案查到的就自己查**，不要問維護者。
- **回答含糊就追問**，直到能判斷一個做法對不對，例如「要快」要問到具體的數字或情境。
- **與先前決策矛盾時**，指出兩邊，要求取捨。
- **先問 constitution，再逐一問每個功能。** 先列出功能清單與相依關係，再深入每個功能的使用者情境、範圍與邊界情況。
- **技術選型留給 plan。** 語言、框架、資料庫這類問題不要討論，記錄下來就繼續。

**每個決定後都更新進度檔**，內容是下方的決策摘要，再加上目前討論到的功能。不要寫入機密值。建立進度檔時，把 `sdd-grill-progress.md` 加入 `.specify/.gitignore`，它不入庫。

維護者要結束時，呈現目前的摘要，保留進度檔，然後停止。

## 4. 決策摘要

所有決策都有結論或已明確延後時，呈現摘要並請維護者確認：

- **已決定**：constitution 的原則、每個功能的決定
- **已延後**：之後再決定的事項與原因
- **留給 plan**：技術選型等問題
- **功能順序**：依相依關係排列

## 5. 產生文件

確認後才進行。文件使用專案既有文件的語言；沒有或無法判斷時用繁體中文，MUST、SHOULD 等規範詞保留英文。把語言要求寫進傳給 Spec Kit 的內容。

1. 用 Skill 工具呼叫 `speckit-constitution`，傳入確認後的原則，並要求它只使用這些內容，不要加入未確認的規則。
2. 依相依順序，為每個功能各呼叫一次 `speckit-specify`，傳入該功能的決定；已延後的事項寫進 Assumptions。被依賴的功能排在前面，讓編號等於建議的施工順序。

無法呼叫這些 skill 時，回報並停止，保留進度檔，不要自行寫出文件。

產生後比對 constitution 與確認的內容，移除多出來的規則；要保留的先問維護者。

## 6. 收尾

Spec Kit 用 `.specify/feature.json` 決定目前處理哪個功能，所以最後一定要處理：

1. 產生多份 spec 時，把 `.specify/feature.json` 的 `feature_directory` 設為這批的第一份，例如 `{"feature_directory": "specs/001-example"}`；檔案不存在就建立。不要問維護者，這一步是固定流程。只有 `.claude/skills/speckit-specify/SKILL.md` 沒有提到 `feature_directory`，表示 Spec Kit 已改變做法時，才不要寫入，改為回報。
2. 刪除進度檔。
3. 列出每份 spec 的路徑、相依關係與建議順序。
4. 說明下一步是 `/speckit-plan`，以及切換功能要改 `.specify/feature.json` 的 `feature_directory`，切換 git 分支不會跟著切換。

然後停止，不要執行 plan。
