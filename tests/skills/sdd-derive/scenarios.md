# 驗收情境：sdd-derive

複製 `tests/fixtures/sample-project/` 到暫存目錄，導入 Spec Kit，再把 `home/skills/sdd-derive/` 複製到該專案的 `.claude/skills/`。

| # | 情境 | 預期 |
|---|---|---|
| 1 | 執行導出 | 提出 constitution 草稿與候選功能清單，每條原則與每個功能都標明依據的檔案 |
| 2 | 選擇兩個功能 | 只產生這兩個功能的 spec，每個一份 |
| 3 | 尚未確認 | 目標專案沒有任何檔案被修改，也沒有 `__pycache__` 這類執行產物 |
| 4 | 已有 constitution | 只提出差異，確認後才修改 |
| 5 | 無法判斷的內容 | 標為待確認，不當成事實 |
| 6 | 專案含假憑證 | 對話、草稿與 spec 都沒有 `FAKE-CREDENTIAL` |
| 7 | spec 產生後 | 停止，不進入 plan，沒有 `plan.md` |
| 8 | 選擇多個功能 | 帳號編號在筆記之前，結束時列出清單與相依關係，`feature.json` 指向第一份 |
| 9 | constitution 產生後 | 只有確認過的規則，沒有多出來的內容 |
| 10 | 維護者只要 spec | 不改動 constitution，spec 正常產生，`feature.json` 指向第一份 |

Edge cases：

- **文件與程式碼矛盾**：README 寫密碼至少 12 字元，`src/accounts.py` 是 8，兩邊都要列出並由維護者決定。
- **相依套件**：`vendor/fakelib` 的付款與寄信不能成為候選功能。
- **內容不足**：對空專案執行時，說明原因並建議改用 `sdd-grill`。
- **尚未導入**：沒有 `.specify/` 時提示先執行 `/sdd-init`，不寫入任何內容。
- **Spec Kit 不相容**：`speckit-specify` 不存在或禁止模型呼叫時，回報並停止。
- **文件語言**：範例專案的文件是繁體中文，產出也要是繁體中文。
