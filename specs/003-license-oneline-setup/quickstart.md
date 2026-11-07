# Quickstart: 驗證授權聲明與一行指令設定

**第 3 到第 6 段要在 Linux 與 Windows 各跑一次才算完成。** 指令介面見 [contracts/setup-cli.md](contracts/setup-cli.md)，紀錄內容見 [data-model.md](data-model.md)。

## 前置條件

- 開發機已安裝 `uv`、`git`，在 repo 根目錄執行第 1、2 段
- 乾淨環境：Linux 用容器或虛擬機，Windows 用虛擬機或新機器。Windows Sandbox 可能沒有 winget，只適合驗證無法自動安裝 git 的情境
- repo 公開前，用 `CLAUDE_DOTFILES_REPO` 指向本機 clone 或掛載的目錄，並直接執行 `tools/setup.sh` 或 `tools/setup.ps1`；clone 不在預設位置時要加 `--dir` 或 `-Dir`

## 1. 自動化測試

```text
uv run -m unittest discover -s tests
```

預期：全部通過。Linux 上 `tests/test_setup_scripts_windows.py` 顯示為略過，不算通過；Windows 上這組測試不得略過，否則不算驗收。

## 2. 授權（US2）

1. 對照 `apache.org/licenses/LICENSE-2.0.txt` 與 `LICENSE`，確認完全相同。
2. 確認 `THIRD_PARTY_NOTICES.md` 列出所有 Spec Kit 路徑與 MIT 條款，README 有連結。
3. 執行 `uv run tools/repo_guard.py --all`。

預期：內容相同，檢查通過。

## 3. 乾淨環境的設定（US1）

1. 在乾淨環境貼上一行指令，記下開始與結束時間。
2. 檢查 `git --version`、`uv --version`、`claude --version`。
3. 在 clone 內執行 `uv run tools/dotfiles.py status`。

預期：除了系統權限提示，不需要其他操作（SC-001）；10 分鐘內完成（SC-002）；狀態為 `clean`；摘要列出已安裝工具與登入提示。

## 4. 重複執行與更新（US1）

1. 再執行兩次，比對 `~/.claude/` 與 clone 的內容（SC-003）。
2. 在來源 repo 新增一個 commit，再執行一次。
3. 在 clone 內留下未提交的改動，再執行一次，然後還原。

預期：前兩次沒有變更；第 2 步更新並重新部署；第 3 步停止，改動還在，結束碼非零。

## 5. 開發設定（US3）

| 情境 | 預期 |
|---|---|
| 不加開發選項 | 本機 `user.email` 與 hook 都沒有變化 |
| 開發選項加 noreply 地址 | 本機 `user.email` 正確，`repo_guard.py --status` 為 `enabled`，全域設定沒有變化 |
| 開發選項加一般 email | 停止，沒有部署也沒有設定變更 |
| 開發選項但沒有 email，且 clone 未設定 noreply | 停止，訊息說明如何提供 |
| 暫時放一個其他工具的 `pre-commit` | 不被覆蓋，摘要回報，結束碼 1 |
| clone 原本就已啟用防護 | 成功；之後解除時，原有的 hook 仍保留 |
| 沒有本機識別清單 | 其餘完成，摘要提示如何建立 |

## 6. 解除（US4）

1. 設定前記錄 `~/.claude/` 所有檔案的雜湊值；用開發選項完成設定。
2. 執行 `uv run <clone>/tools/machine_setup.py remove`。
3. 比對雜湊值，並檢查 hook 與本機 `user.email`。

預期：逐檔相同（SC-004）；hook 已移除，email 回到設定前的值；工具與 clone 還在，摘要列出移除方式。在真實機器上驗收時，Claude Code 自己寫入 `~/.claude/` 的檔案不列入比對。

## 7. 失敗情境

兩個系統的自動化測試都涵蓋：不支援的作業系統、版本過舊、無法安裝 git、目標目錄不是這個 repo、clone 分岔、下載失敗。另外在 Windows 互動視窗手動選一項確認：訊息指出失敗步驟，視窗沒有被關閉。

## 8. 公開後的最終驗收

repo 公開後，在 Linux 與 Windows 的乾淨環境各用 README 上的真實指令跑一次第 3 段；確認 GitHub 頁面把授權顯示為 Apache-2.0（SC-006）。**這一步完成，這個功能才算完成。**
