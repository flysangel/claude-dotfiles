---

description: "Task list for the license and one-line setup"
---

# Tasks: 授權聲明與一行指令設定

**Input**: Design documents from `specs/003-license-oneline-setup/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/setup-cli.md, quickstart.md

**Tests**: 包含測試任務。spec FR-021 要求設定與解除有自動化測試，憲章原則 V 要求安裝與解除有驗證步驟。

**Organization**: 依 user story 分組。US1 與 US2 同為 P1 且彼此獨立，US2 可以先做。

**Windows**: `tests/test_setup_scripts_windows.py` 在 Linux 上會略過，寫好時尚未執行過，第一次實際執行是 T033，屆時可能需要修正。

**Commit**: 每完成一項異動就在目前分支 commit，不直接提交到 `main`，也不 push，不得用 `--no-verify` 略過 hook。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可以平行進行（不同檔案，且不依賴未完成的任務）
- **[Story]**: 所屬的 user story（US1 到 US4）

## Path Conventions

路徑相對於 repo 根目錄。工具在 `tools/`，測試在 `tests/`。測試一律使用暫存目錄與隔離的 `HOME`，不得碰使用者真正的 `~/.claude/`；測試資料只用假值與 `@users.noreply.github.com` 的假地址。

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 建立隔離的測試環境，後續測試才不會碰到真實設定

- [X] T001 [P] 建立 `tests/test_machine_setup.py` 的共用測試基底：暫存 `HOME`、一個本機 bare repo 當來源、一個由它 clone 出來的 repo（內含 `tools/` 與 `home/` 的複製），並用 `sys.executable` 執行其中的 `tools/machine_setup.py`；基底要斷言 `Path.home()` 與 `--target` 都在暫存目錄內
- [X] T002 [P] 建立 `tests/test_setup_scripts.py` 的共用測試基底，只在 Linux 執行：把假的 `uname`、`sudo`、`apt-get`、`dnf`、`pacman`、`curl`、`wget`、`uv`、`claude`、`git` 放進只含它們與必要系統指令的 `PATH`，每個假工具都把呼叫記錄到檔案；假 `git` 的 `clone` 與 `remote` 轉給真 git，版本字串可由環境變數設定
- [X] T003 [P] 建立 `tests/test_setup_scripts_windows.py` 的共用測試基底，條件為 `os.name == "nt"` 且有 `powershell` 或 `pwsh`（`skipUnless`）：把假的 `.cmd` 工具（`winget`、`git`、`uv`、`claude`、`powershell`）放進隔離的 `PATH` 並記錄呼叫，用絕對路徑啟動真正的 PowerShell 執行 `tools/setup.ps1`，`USERPROFILE` 指向暫存目錄

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 設定紀錄與 CLI 骨架，US1、US3、US4 都會用到

**⚠️ CRITICAL**: 完成前不要開始 US1、US3、US4；US2 不受影響

- [X] T004 在 `tests/test_machine_setup.py` 加入設定紀錄測試：路徑為 `~/.config/claude-dotfiles/setup.json`；欄位為 `version`（目前為 `1`）、`clone`、`installed_tools`（值為 `uv`、`git`、`claude`，多次執行取聯集）、`dev`（沒做過開發設定時為 `null`）；`dev.previous_email` 只在第一次開發設定時寫入，重複執行不覆蓋；原子寫入；Linux 上權限為 `600`；格式錯誤時 `install` 與 `remove` 都停止並回報，不猜測內容
- [X] T005 建立 `tools/machine_setup.py`：使用與其他工具相同的 inline script metadata（`requires-python = ">=3.11"`、無相依），`ROOT` 由 `__file__` 推得；以 `argparse` 實作 `install`（`--dev`、`--email`、`--force`、`--installed`、`--target`）與 `remove`（`--target`）兩個子指令骨架；重設輸出編碼（同 `tools/dotfiles.py`）；結束碼依 `specs/003-license-oneline-setup/contracts/setup-cli.md`；實作設定紀錄的載入與原子寫入，讓 T004 通過

**Checkpoint**: 紀錄可以讀寫，user story 可以開始

---

## Phase 3: User Story 1 - 新機器貼一行就完成設定 (Priority: P1) 🎯 MVP

**Goal**: 在 Linux 與 Windows 貼一行指令，補齊工具、取得 repo 並完成部署

**Independent Test**: 在只有作業系統的乾淨環境各貼一次指令，確認設定已部署且 `dotfiles.py status` 為 `clean`

### Tests for User Story 1

- [X] T006 [US1] 在 `tests/test_setup_scripts.py` 加入事前檢查測試：`uname` 為 `Darwin` 或 `MINGW64_NT` 時不做任何變更且結束碼 1；既有 git 低於 2.20 或 uv 低於 0.4.0 時，在安裝任何東西前停止、列出所需版本且不升級；檢查時不呼叫任何安裝程式
- [X] T007 [US1] 在 `tests/test_setup_scripts.py` 加入工具安裝測試：只安裝缺少的工具，既有工具沒有收到任何安裝呼叫；依序偵測 `apt-get`、`dnf`、`pacman` 安裝 git；非 root 才用 `sudo`；`sudo` 不存在或失敗、沒有套件管理工具時，停止並列出手動方式；uv 與 Claude Code 的官方腳本 MUST NOT 透過 `sudo` 執行；只有 `wget` 時也能下載；下載失敗時回報步驟並停止，失敗訊息列出這次已安裝的工具；安裝後工具只在 `~/.local/bin` 時，同一次執行仍能繼續；實際安裝的工具以 `--installed` 傳給 Python 層
- [X] T008 [US1] 在 `tests/test_setup_scripts.py` 加入 clone 與管線測試：預設 clone 到 `$HOME/claude-dotfiles`，`--dir` 可覆寫；`CLAUDE_DOTFILES_REPO` 改變來源與比對對象；`origin` 比對依 research 第 8 節，同一個 repo 的 HTTPS、SSH、大小寫不同與沒有 `.git` 結尾的網址都算相符；目標存在但不是 git repo，或 `origin` 不符時，不變更目錄、不執行其中的程式（放一個會留下記號的假 `tools/machine_setup.py` 驗證）且結束碼 1；以 `cat tools/setup.sh | bash -s -- --force` 執行時參數正確傳遞；截斷的腳本內容不會執行任何步驟；子程序不會讀走管線中的腳本
- [X] T009 [US1] 在 `tests/test_setup_scripts.py` 加入兩支入口的靜態測試（所有平台都跑）：`tools/setup.sh` 與 `tools/setup.ps1` 只含 ASCII；`tools/setup.ps1` 沒有 `exit` 陳述式，第三方安裝腳本都透過子程序 `powershell -NoProfile -ExecutionPolicy Bypass -Command` 執行；兩支的下載網址都是 `https://`，且只來自 research 第 4 節的來源與此 repo
- [X] T010 [US1] 在 `tests/test_setup_scripts_windows.py` 加入行為測試，涵蓋與 T006 到 T008 相同的情境：只安裝缺少的工具；既有 git 或 uv 版本過舊時在安裝前停止；winget 不存在或安裝失敗時列出手動方式；官方腳本下載失敗時回報步驟並列出已安裝的工具；安裝後能在同一次執行找到工具；預設 clone 到 `%USERPROFILE%\claude-dotfiles`，`-Dir` 可覆寫；目標不是這個 repo 時不執行其中的程式；`-Dev`、`-Email`、`-Force` 正確傳給 Python 層；失敗時以 `throw` 回報，`try`/`catch` 內的後續陳述式仍會執行（視窗不會被關閉），透過 `-Command` 執行時結束碼為 1。另加一項測試，在非 Windows 的 `pwsh` 上也會執行：不支援的系統在任何變更前停止
- [X] T011 [US1] 在 `tests/test_machine_setup.py` 加入 clone 更新測試：來源有新 commit 且可快轉時更新，並重新執行自己恰好一次；`git status --porcelain` 有內容時停止、內容不變、不部署且結束碼 1；已分岔時同樣停止；本機領先或沒有 upstream 時不更新、繼續部署並提示；更新失敗時回報步驟
- [X] T012 [US1] 在 `tests/test_machine_setup.py` 加入部署與摘要測試：呼叫 `tools/dotfiles.py deploy --target`；連續執行兩次時 `--target` 內容與 clone 都不變，並回報已是最新狀態；既有 `CLAUDE.md` 先備份；同名且不受管的 skill 使結束碼為 2，加 `--force` 才取代；摘要符合 contract 的格式，含已安裝工具、repo 位置與部署結果；有安裝工具時提示開新的終端機；`claude auth status` 回報已登入時不提示登入，未登入或無法判斷時提示；設定紀錄的 `clone` 指向另一個仍存在的目錄時停止且結束碼 1，目錄已不存在才改寫；輸出不含 email 的值

### Implementation for User Story 1

- [X] T013 [US1] 建立 `tools/setup.sh`：全部內容包在函式內且最後一行才呼叫；子程序 stdin 導向 `/dev/null`；只含 ASCII；依序確認作業系統、檢查既有工具版本（git 2.20、uv 0.4.0）、安裝 git、uv、Claude Code、確認 `origin`（比對規則見 research 第 8 節）或建立 clone，最後執行 `uv run <clone>/tools/machine_setup.py install --installed ...` 並傳回其結束碼；接受 `--dir`、`--dev`、`--email`、`--force`，讓 T006 到 T008 通過
- [X] T014 [US1] 建立 `tools/setup.ps1`，流程與 T013 相同：開頭為 `param` 區塊（`-Dir`、`-Dev`、`-Email`、`-Force`）；用 `throw` 回報失敗，不用 `exit`；git 用 `winget install --id Git.Git`，uv 與 Claude Code 在子程序內執行官方腳本並以結束碼判斷；安裝後重新讀取系統與使用者的 `Path`，並加入 `%USERPROFILE%\.local\bin`；非 Windows 時任何變更前停止；只含 ASCII，讓 T009、T010 通過
- [X] T015 [US1] 在 `tools/machine_setup.py` 實作 clone 更新：依 research 第 8 節處理未提交改動、分岔、可快轉、本機領先與沒有 upstream；快轉後以環境變數防止重複，重新執行自己一次，讓 T011 通過
- [X] T016 [US1] 在 `tools/machine_setup.py` 實作 `install` 的部署與摘要：檢查紀錄的 `clone` 是否指向另一個仍存在的目錄，再寫入 `clone` 與 `installed_tools`，再以 `sys.executable` 執行 `tools/dotfiles.py deploy`；傳遞 `--force` 與 `--target`；用 `claude auth status` 判斷登入狀態，無法判斷時仍提示登入；依 contract 顯示摘要，讓 T012 通過
- [ ] T017 [US1] 在 Linux 容器或虛擬機（`CLAUDE_DOTFILES_REPO` 指向本機 clone）完成 `specs/003-license-oneline-setup/quickstart.md` 第 3、4 段，把實測的 git 與 uv 版本、耗時與結果記錄到 `specs/003-license-oneline-setup/research.md`；若 git 2.20 或 uv 0.4.0 的下限不正確，同步修正 research、`tools/setup.sh` 與 `tools/setup.ps1`

**Checkpoint**: Linux 上可從乾淨環境完成設定；Windows 的測試已寫好但尚未執行，要到 T033 才算驗收

---

## Phase 4: User Story 2 - 專案有明確的授權 (Priority: P1)

**Goal**: 根目錄有 Apache-2.0 授權，並保留 Spec Kit 的 MIT 聲明

**Independent Test**: 根目錄有未改動的 Apache-2.0 全文，第三方聲明涵蓋 Spec Kit，兩個檔案都能通過 commit 防護

### Tests for User Story 2

- [X] T018 [P] [US2] 在 `tests/test_content.py` 加入授權測試：`LICENSE` 的 SHA-256 等於 T019 記錄的值；`THIRD_PARTY_NOTICES.md` 含 `Copyright GitHub, Inc.`、`MIT License` 與 `github/spec-kit`，並涵蓋 `.specify/` 與 `.claude/skills/speckit-*/`，也明確排除 `.specify/memory/constitution.md`；`README.md` 連到這兩個檔案，且不再有授權尚未決定的說明

### Implementation for User Story 2

- [X] T019 [US2] 下載 `https://www.apache.org/licenses/LICENSE-2.0.txt` 存成 `LICENSE`，內容不做任何改動；把算出的 SHA-256 寫進 T018 的測試，並把 `LICENSE` 加入 `.repo-allowlist`
- [X] T020 [US2] 建立 `THIRD_PARTY_NOTICES.md`，列出來自 Spec Kit 1.2.6 的路徑（`.specify/`，不含 `.specify/memory/constitution.md`；`.claude/skills/speckit-*/`）、上游 `https://github.com/github/spec-kit` 與 v1.2.6 `LICENSE` 的完整 MIT 條款，並把它加入 `.repo-allowlist`
- [X] T021 [US2] 在 `README.md` 新增授權段落：`Copyright 2026 flysangel`、以 Apache-2.0 授權、連到 `LICENSE` 與 `THIRD_PARTY_NOTICES.md`；從「已知限制」的公開順序移除授權尚未決定的句子；執行 `uv run tools/repo_guard.py --all` 確認通過

**Checkpoint**: 授權完成，不依賴其他 story

---

## Phase 5: User Story 3 - 維護者一併完成開發設定 (Priority: P2)

**Goal**: 開發選項一次完成提交身分與 commit 防護

**Independent Test**: 用開發選項與假的 noreply 地址執行，確認本機身分與防護都正確；不加選項時兩者都沒有變化

**依賴**: US1

### Tests for User Story 3

- [X] T022 [US3] 在 `tests/test_machine_setup.py` 加入開發設定測試：`--dev --email` 時 email 只寫入 clone 的本機設定，全域設定不變；只接受 `@users.noreply.github.com` 結尾，`noreply@example.com` 與一般地址都被拒絕，沿用 clone 既有地址時也採用同一標準；無效或缺少 email，且 clone 尚未設定 noreply 地址時，不做開發設定也不部署且結束碼 1；clone 已有 noreply 地址且未提供 email 時沿用，`dev.email_set` 為 `null`；沒有 `--dev` 時身分與 hook 都不變；`dev.previous_email` 在變更前寫入，重複執行不覆蓋；輸出不含 email 的值
- [X] T023 [US3] 在 `tests/test_machine_setup.py` 加入 hook 與識別清單測試：安裝前 `--status` 第一行為 `not-installed` 且 `repo_guard.py --install-hook` 成功時 `dev.hook_installed` 為真；原本就已啟用時為假；已為真時重複執行不改變；摘要顯示 `--status` 第一行；其他工具佔用 hook 時不覆蓋、仍完成部署、摘要回報且結束碼 1；設定 `core.hooksPath` 時顯示 `unverified`；本機識別清單不存在時（以 `REPO_GUARD_IDENTITY_FILE` 隔離）摘要提示如何建立，不影響結束碼，也不產生清單；沒有 `--dev` 時不提示
- [X] T024 [P] [US3] 在 `tests/test_setup_scripts.py` 加入參數傳遞測試：`--dev --email <假地址>` 經由管線傳到 Python 層，`--email` 缺少值時停止

### Implementation for User Story 3

- [X] T025 [US3] 在 `tools/machine_setup.py` 實作開發設定：參數檢查放在更新 clone 與部署之前；先寫入 `dev` 紀錄，再變更 `user.email`（僅 `--local`）；以 `sys.executable` 執行 `tools/repo_guard.py --install-hook` 與 `--status`；依 contract 的行為表決定結束碼與摘要，讓 T022、T023 通過；入口腳本已在 T013、T014 接受開發選項，同時確認 T024 通過

**Checkpoint**: 維護者的新 clone 可以一行完成開發設定

---

## Phase 6: User Story 4 - 解除設定 (Priority: P2)

**Goal**: 一個指令還原 `~/.claude/` 與開發設定，並說明留下了什麼

**Independent Test**: 記錄 `--target` 的雜湊值，設定後解除再比對，內容逐檔相同

**依賴**: US1；開發設定的還原依賴 US3

### Tests for User Story 4

- [X] T026 [US4] 在 `tests/test_machine_setup.py` 加入解除測試：`--target` 設定前後逐檔雜湊相同；沒有紀錄時不報錯也不變更；`dev.hook_installed` 為真時只移除自己的 hook，其他工具的 hook 保留；為假時原有的防護 hook 也保留；目前 `user.email` 等於 `dev.email_set` 才還原為 `dev.previous_email` 或移除，已被使用者改動就保留並回報；工具與 clone 保留，摘要列出它們與官方解除安裝連結；全部成功才刪除紀錄，目錄空了也一併移除，但 `identity.txt` 存在時保留目錄；中途失敗後紀錄仍在，可以重新執行；紀錄不寫入 `--target`

### Implementation for User Story 4

- [X] T027 [US4] 在 `tools/machine_setup.py` 實作 `remove`，依 `specs/003-license-oneline-setup/data-model.md` 的「解除時的還原」表處理，讓 T026 通過

**Checkpoint**: 完整的設定與解除循環通過

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 文件、整體驗證與跨平台驗收

- [ ] T028 改寫 `README.md` 的「安裝」段落：把 contract 的一行指令放在最前面，含 `wget` 寫法、開發選項與解除指令；說明如何先下載再檢視腳本；手動步驟移到維護章節；保留本機識別清單與 `--force` 的說明；註明 repo 公開前無法匿名使用，要先 clone 並直接執行入口腳本，clone 不在預設位置時要加 `--dir` 或 `-Dir`
- [ ] T029 更新 `README.md` 的「已知限制」：列出解除時保留工具與 clone、git 自動安裝只支援 apt、dnf、pacman 與 winget、一行指令的信任模型
- [ ] T030 執行 `uv run -m unittest discover -s tests`、`uv run tools/repo_guard.py --all` 與 `uv run tools/repo_guard.py --history`，全部通過；把在這台機器略過的測試（`tests/test_setup_scripts_windows.py`）明確記在 `specs/003-license-oneline-setup/research.md`
- [ ] T031 確認這個功能沒有改動 `home/`（`git diff --stat main...HEAD -- home/` 沒有輸出），因此不需要執行 `/doctor prompt-audit`；有改動時就要執行
- [ ] T032 在 Linux 容器或虛擬機完成 `specs/003-license-oneline-setup/quickstart.md` 第 5、6 段與第 7 段的自動化部分，結果記錄到 `specs/003-license-oneline-setup/research.md`
- [ ] T033 請維護者在 Windows 機器先執行 `uv run -m unittest discover -s tests`，確認全部通過且 `tests/test_setup_scripts_windows.py` 沒有被略過，再完成 `specs/003-license-oneline-setup/quickstart.md` 第 3 到第 7 段（`CLAUDE_DOTFILES_REPO` 指向本機 clone），可與 001 的 T029 一起進行；依結果修正 `tools/setup.ps1`，把結果記錄到 `specs/003-license-oneline-setup/research.md`，並更新 `README.md` 的「目前狀態」
- [ ] T034 公開後（維護者另外決定，先完成 001 的 T030），請維護者在 Linux 與 Windows 乾淨環境完成 `specs/003-license-oneline-setup/quickstart.md` 第 8 段，確認 GitHub 把授權顯示為 Apache-2.0，並把結果記錄到 `specs/003-license-oneline-setup/research.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup（Phase 1）**：沒有前置
- **Foundational（Phase 2）**：依賴 Setup；擋住 US1、US3、US4
- **US1（Phase 3）**：依賴 Foundational
- **US2（Phase 4）**：沒有前置，可以最先做
- **US3（Phase 5）**：依賴 US1
- **US4（Phase 6）**：依賴 US1；開發設定的還原依賴 US3
- **Polish（Phase 7）**：依賴全部 story；T034 另外依賴 repo 公開

### User Story Dependencies

```text
US2（獨立）

Setup → Foundational → US1 → US3 → US4 → Polish → T033（Windows）→ 公開 → T034
```

### Within Each User Story

- 測試先寫，確認失敗後再實作
- 同一個測試檔的任務不標 [P]，避免衝突

## Parallel Opportunities

- T001、T002 與 T003：不同測試檔
- US1 與 US2 可以同時進行：只有 US2 會動 `tests/test_content.py` 與授權檔案
- T006 到 T009（`tests/test_setup_scripts.py`）、T010（`tests/test_setup_scripts_windows.py`）與 T011、T012（`tests/test_machine_setup.py`）：三組可以同時進行，同組內依序
- T013 與 T015：不同檔案；T014 要等 T013 定下流程，方便對照
- T024 與 T022、T023：不同測試檔

### Parallel Example: User Story 1

```text
T006 → T007 → T008 → T009（tests/test_setup_scripts.py）
T010（tests/test_setup_scripts_windows.py）
T011 → T012（tests/test_machine_setup.py）
T013（tools/setup.sh）與 T015（tools/machine_setup.py）同時實作
```

## Implementation Strategy

### MVP First

1. 先完成 US2：只有文件，風險最低，也是公開的前提之一。
2. 完成 Setup、Foundational 與 US1，在 Linux 容器驗證。
3. 停下來確認一行指令的行為符合預期。

### Incremental Delivery

1. US3：維護者的新 clone 不用再手動設定。
2. US4：補齊還原。
3. Polish 與 T033 的 Windows 驗收。
4. T034 在公開後完成。

---

## Notes

- 一行指令從 `main` 下載，所以這個分支合併到 `main` 之前，真實網址上還沒有腳本；合併與 push 都要維護者另外同意
- T034 完成前，這個功能不算完成
- 公開與 push 是對外操作，這份任務清單不會自行進行
- 測試不得真的安裝工具，也不得連到 `astral.sh`、`claude.ai` 或 GitHub；真實安裝只在 T017、T032、T033、T034 的乾淨環境驗證
- `tools/machine_setup.py` 與入口腳本的輸出不得包含 email 的值與使用者的識別清單內容
