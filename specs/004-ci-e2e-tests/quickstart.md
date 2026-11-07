# Quickstart: 驗證持續整合測試與 E2E 測試

workflow 只能在 GitHub 上驗證。第 3 段以後的每一次 push 都要維護者同意。介面見 [contracts/](contracts/)，結果格式見 [data-model.md](data-model.md)。

## 1. 本機測試

```text
uv run -m unittest discover -s tests
REQUIRED_TEST_GROUPS=setup-sh uv run -m unittest tests.test_setup_scripts
REQUIRED_TEST_GROUPS=powershell uv run -m unittest tests.test_setup_scripts_windows
uvx check-jsonschema --builtin-schema vendor.github-workflows .github/workflows/ci.yml
```

預期：第一行全部通過；第二行在 Linux 通過；第三行在沒有 PowerShell 的機器上**失敗**，證明閘門有效；schema 檢查通過。

## 2. 本機容器跑 E2E 驅動

用 podman 依 research 第 5 節準備四個環境，執行 `tests/e2e/linux.sh`。

預期：每個環境五個階段都是 `PASS`；`minimum` 環境的 `setup` 摘要顯示沒有安裝任何工具。

## 3. 第一次 push

push 分支後，在 GitHub 的 Actions 頁面確認：

- 七個 job 都完成，總時間在 20 分鐘內（SC-002）。
- `unit-windows` 的 PowerShell 5.1 與 7 都有執行，略過數符合預期。
- `e2e-windows` 的 summary 顯示 winget 是否可用；不可用時 `git` 安裝列為 `UNVERIFIED`。
- 記錄每個 job 的實際分鐘數，更新 research 第 7 節的估算。

## 4. 故意失敗（每項驗證後就刪除該分支）

| 情境 | 做法 | 預期 |
|---|---|---|
| 只在 Windows 失敗的測試 | 加一個在 Windows 上 `fail()` 的測試 | `unit-windows` 失敗並指出測試名稱，`unit-linux` 通過（SC-003） |
| 必須執行的測試被略過 | 在 `unit-windows` 讓 PowerShell 找不到 | job 失敗，不是略過 |
| 工具安裝壞掉 | 把 `setup.sh` 與 `setup.ps1` 的 uv 安裝網址改成不存在的路徑 | 每個 E2E 環境的 `setup` 為 `FAIL`，說明指出下載來源（SC-004） |
| 推上機密 | 以 `--no-verify` 推一個含假 token 的 commit | `guard` 失敗，日誌不含 token 完整值（SC-005） |

## 5. 公開後

push 到 `main` 時，確認 `ubuntu-public` 與 `windows-public` 都有結果；這一步同時完成 003 的 T034。
