---
name: sdd-init
description: Add the latest stable Spec Kit to the current project without overwriting existing files, or remove it again. Run manually with /sdd-init.
argument-hint: "[remove [--all]]"
disable-model-invocation: true
---

在目前的專案執行以下指令，`$ARGUMENTS` 空白時就是導入：

```text
uv run "${CLAUDE_SKILL_DIR}/scripts/sdd_init.py" $ARGUMENTS
```

只執行這個指令，不要手動建立或修改 Spec Kit 的檔案。

把結果轉述給我：

- 安裝的版本、建立與略過的檔案，以及腳本輸出的下一步建議。
- 結束碼不是 0 時，說明原因與處理方式，不要自行重試或改用其他方式安裝。結束碼 3 表示缺少工具或無法取得版本，1 表示導入或移除失敗。
