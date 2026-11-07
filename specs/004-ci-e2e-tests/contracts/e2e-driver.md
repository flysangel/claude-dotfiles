# Contract: E2E 驅動腳本

## Linux：`tests/e2e/linux.sh`

在拋棄式容器內以要測試的使用者身分執行；不得在開發機上直接執行，因為它會真的安裝工具並改動家目錄。

```text
bash tests/e2e/linux.sh <環境名稱> <bare repo 路徑>
```

| 環境變數 | 意義 |
|---|---|
| `E2E_SETUP_URL` | 有值時，`setup` 階段改用這個網址的一行指令（公開後的真實網址測試） |
| `GITHUB_STEP_SUMMARY` | 有值時，把結果行附加到這個檔案 |

容器的準備（安裝 `curl`、建立使用者、版本下限環境的工具）由 workflow 負責，不在驅動腳本內。

## Windows：`tests/e2e/windows.ps1`

在 Windows runner 上以系統管理員身分執行；它會改名 `C:\Program Files\Git`，不得在個人電腦上執行。

```text
powershell -NoProfile -ExecutionPolicy Bypass -File tests\e2e\windows.ps1 -BareRepo <路徑> [-SetupUrl <網址>]
```

開始前：隱藏既有工具並確認找不到；處理 winget（見 research 第 6 節）。入口腳本一律以 Windows PowerShell 5.1 執行。

## 共通

- 階段、結果格式與判定見 [data-model.md](../data-model.md)。
- 結束碼：任一階段 `FAIL` 為 1，否則為 0。
- 每個階段的輸出以 GitHub Actions 的群組語法折疊，失敗時可以展開查看。
