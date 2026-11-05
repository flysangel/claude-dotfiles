# Contract: 設定檢視

```text
uv run tools/review_settings.py [--path <file>]
```

`--path` 預設為 `~/.claude/settings.json`。

## 行為

- 只讀取，不修改原始檔，也不在 repo 內產生檔案。
- 每個頂層項目都有一筆分類：`可共用`、`含機密`、`機器專屬` 或 `待判斷`。
- 巢狀結構會往下檢查，頂層項目取其中最嚴重的分類，並列出觸發的鍵路徑。嚴重度由高到低為含機密、機器專屬、待判斷、可共用。
- **輸出不得包含設定值。** 鍵名符合憑證或識別規則時，也要遮蔽。

## 輸出

```text
可共用    theme
機器專屬  hooks  (hooks.Stop[0].hooks[0].command)
含機密    env    (env.API_KEY)
待判斷    experimentalThing

共 4 項：可共用 1、含機密 1、機器專屬 1、待判斷 1
```

## 結束碼

| 碼 | 意義 |
|---|---|
| 0 | 完成，不論分類結果 |
| 3 | 檔案不存在或不是有效的 JSON；訊息不得包含檔案內容 |
