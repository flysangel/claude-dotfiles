# Contract: CI workflow

檔案：`.github/workflows/ci.yml`

## 觸發與共通設定

| 項目 | 設定 |
|---|---|
| 觸發 | 每次 push 到任何分支；另可手動觸發 |
| 取消 | 同一分支有新的 push 時取消尚未完成的執行 |
| 權限 | `contents: read`，不使用任何 secret；checkout 設 `persist-credentials: false` |
| Action | 只用 `actions/checkout` 與 `astral-sh/setup-uv`，固定到 commit SHA |

## Job

| Job | Runner | 內容 | 失敗條件 |
|---|---|---|---|
| `unit-linux` | `ubuntu-latest` | `REQUIRED_TEST_GROUPS=setup-sh,powershell`、`SETUP_PS1_TESTS=1`、`SETUP_PS1_SHELL=pwsh`、`RUN_NETWORK_TESTS=1`，執行 `uv run -m unittest discover -s tests -v` | 任一測試失敗，或必須執行的測試被略過 |
| `unit-windows` | `windows-latest` | `REQUIRED_TEST_GROUPS=powershell`；先以 `SETUP_PS1_SHELL=powershell` 跑全部測試，再以 `pwsh` 跑 `tests.test_setup_scripts_windows` | 同上 |
| `guard` | `ubuntu-latest` | `uv run tools/repo_guard.py --history --without-identity` | 任一違規 |
| `e2e-linux` | `ubuntu-latest`，matrix 四個環境 | 見 [e2e-driver.md](e2e-driver.md) | 任一階段 `FAIL` |
| `e2e-windows` | `windows-latest` | 見 [e2e-driver.md](e2e-driver.md) | 任一階段 `FAIL` |

所有 job 都取完整歷史。各 job 互相獨立，不設相依，讓一次 push 能同時看到全部結果。

## 結果的呈現

- 每個 job 的 summary 列出：測試的通過、失敗與略過數，或 E2E 每個階段的結果行。
- `UNVERIFIED` 的項目在 summary 中獨立列出。
- 日誌與 summary 不得含真實 email 或機密原文。
