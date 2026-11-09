# Contract: 測試閘門與入庫檢查的 CI 模式

## `tests/gates.py`

```text
requires(group: str, condition: bool, reason: str) -> decorator
```

| `REQUIRED_TEST_GROUPS` 含 `group` | `condition` | 結果 |
|---|---|---|
| 否 | 真 | 執行 |
| 否 | 假 | 略過，原因為 `reason`（與 `unittest.skipUnless` 相同） |
| 是 | 真 | 執行 |
| 是 | 假 | 每個測試都失敗，訊息說明該群組被要求執行但條件不成立 |

`REQUIRED_TEST_GROUPS` 為逗號分隔；未設定時等同空集合，本機行為不變。

## `SETUP_PS1_SHELL`

`tests/test_setup_scripts_windows.py` 使用的 PowerShell：`powershell` 或 `pwsh`。未設定時沿用目前的選擇（先找 `powershell`，再找 `pwsh`）。指定的程式找不到時，測試視為條件不成立。

## `repo_guard.py --history --without-identity`

修改 `specs/001-repo-commit-guard/contracts/repo-guard.md` 的 `--history`：

| 情況 | 不加選項（不變） | 加 `--without-identity` |
|---|---|---|
| 有識別清單 | 全部規則 | 識別清單以外的全部規則，不讀取清單 |
| 沒有識別清單 | 結束碼 3，不通過 | 執行其餘規則；第一行說明未比對個人識別資訊；結束碼依其餘規則 |

`--without-identity` 只能與 `--history` 一起使用，否則結束碼 3。
