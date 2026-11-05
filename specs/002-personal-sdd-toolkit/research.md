# Research: 個人化 SDD 工具組

驗證環境：Linux、Claude Code 2.1.318、uv 0.13.6、Spec Kit 1.2.6 與 v1.3.0（2026-11-05）。**以下結果都未在 Windows 上實測**，需依 [quickstart.md](quickstart.md) 驗收。

## 1. 腳本語言

- **Decision**: Python 3.11+ 標準庫，以 `uv run` 執行，並在腳本內用 PEP 723 宣告版本需求。
- **Rationale**: Spec Kit 本來就需要 `uv`，所以不會多一個前置工具。`uv run` 也避開 Windows 上 `python` 與 `python3` 名稱不一致的問題。
- **Alternatives**: bash 違反憲章原則 IV；bash 加 PowerShell 要維護兩份邏輯；Node 會多一個前置工具。

## 2. 部署方式

- **Decision**: 複製檔案，並用部署紀錄保存雜湊值與備份位置。
- **Rationale**: Windows 建立 symlink 可能需要額外權限；官方文件也指出 Cowork 工作階段會略過 symlink 形式的 `~/.claude/CLAUDE.md`。
- **Alternatives**: symlink 如上。Claude Code plugin 主要用於發佈 skill，不能解決個人 CLAUDE.md 的部署，仍需第二套機制。

## 3. 機器專屬內容

- **Decision**: 放在 `~/.claude/rules/`。部署與解除部署都不碰這個目錄。
- **Rationale**: 官方文件說明該目錄是使用者層級的規則，適用所有專案，不需要在 CLAUDE.md 加 import，也不會出現外部 import 的核准對話框。
- **Alternatives**: `@~/.claude/...` import 可行，但要多管一個可能不存在的檔案。

## 4. 取得最新版 Spec Kit

- **Decision**: 用 `git ls-remote --tags` 找出最高的穩定版標籤，再執行 `uv tool run --from git+https://github.com/github/spec-kit.git@<tag> specify init ...`。
- **Rationale**: 實測可行，且取得 v1.3.0，比本機已安裝的 1.2.6 新，代表不能依賴本機的 `specify`。測試機上 `uvx` 不在 PATH，但 `uv tool run` 可用，因此使用後者。使用標籤可避免拿到預設分支上尚未發佈的內容。
- **Alternatives**: 本機 `specify` 可能過舊；預設分支不一定穩定。

## 5. 不覆蓋既有內容

- **Decision**: 先把 Spec Kit 初始化到暫存目錄，再把目標專案不存在的檔案複製過去，並記錄建立的檔案清單。
- **Rationale**: 實測 `specify init --here --non-interactive` 在非空目錄會直接失敗，要求加 `--force`，而 `--force` 的說明是「merge/overwrite」，不保證保留既有內容。暫存目錄的做法不依賴上游行為，也讓失敗時不會留下半成品（FR-009、FR-010）。
- **Alternatives**: `--force` 如上；執行前後比對還原則較脆弱。
- **待實作時確認**: 檢查暫存路徑不會被寫進產生的檔案。

## 6. 依作業系統選擇腳本

- **Decision**: Windows 用 `--script ps`，Linux 用 `--script sh`。
- **Rationale**: 實測兩者都會讓 skill 指向對應的腳本目錄。`py` 雖可跨平台，但指令固定為 `python3`，在 Windows 上不一定可用，並且同時帶入 bash 腳本。
- **已知限制**: 一個專案只會有一種腳本。同一專案要在兩個作業系統開發時，另一邊需要對應的 shell，此限制在導入完成時提示。

## 7. Skill 如何產生文件

- **Decision**: `sdd-derive` 與 `sdd-grill` 只負責蒐集與確認，再呼叫專案內的 `speckit-constitution` 與 `speckit-specify`，每個功能呼叫一次 `speckit-specify`。
- **Rationale**: 符合 FR-025，上游範本與編號規則改變時不必跟著改。實測 v1.3.0 的 `speckit-specify` 未禁止模型呼叫。
- **風險**: 「一律最新版」下上游可能改名或禁止模型呼叫。因此 skill 開始前會檢查，不符合就回報並停止。官方文件未明確說明 skill 呼叫 skill 的行為，第一次情境驗收要確認。

## 8. 多份 spec 的接續

- **Decision**: 依相依順序產生 spec，全部完成後把 `.specify/feature.json` 指向第一份。
- **Rationale**: 讀 `.specify/scripts/bash/common.sh` 確認 Spec Kit 依序看 `SPECIFY_FEATURE_DIRECTORY` 與 `feature.json`，不看 git 分支；`feature.json` 也被 gitignore。不處理的話指標會停在最後一份，接著跑 plan 會處理錯功能。
- **Alternatives**: 另做切換工具要多維護一項，維護者未選擇；不處理指標如上。
- **風險**: `feature.json` 的格式屬於上游，改版時可能變動，寫入前要確認檔案存在且有 `feature_directory` 欄位，否則只回報、不寫入。

## 9. Skill 觸發方式

- **Decision**: `sdd-derive`、`sdd-grill` 允許自動觸發；`sdd-init` 設定 `disable-model-invocation: true`，只能手動以 `/sdd-init` 執行。
- **Rationale**: 官方文件建議有副作用、需要自行掌握時機的流程使用此設定。

## 10. 驗證方式

- **Decision**: 腳本用 `unittest` 與暫存目錄測試，不碰真實的 `~/.claude/`；觸發案例用 `claude -p` 手動執行；skill 行為以情境驗收。
- **Rationale**: 觸發測試要呼叫模型，有費用且結果不完全固定，不適合每次執行。
- **已確認**: `claude -p --output-format stream-json --verbose` 的輸出含 `Skill` 工具呼叫，應觸發與不應觸發的樣本都判斷正確。用 haiku 的單次費用不到 $0.01；實際觸發行為可能隨模型不同，正式驗收可用 `--model` 指定。

## 11. 新專案的 git

- **Decision**: 目標不在 git repo 內時，導入成功後才執行 `git init`，不自動 commit；移除時不刪除 `.git`。
- **Rationale**: 實測 v1.3.0 的 `specify init` 不會建立 `.git`，而個人 CLAUDE.md 要求每次異動都 commit。放在最後一步可避免失敗時還要復原 git 狀態；已在上層 git repo 內時不執行。

## 12. 官方文件依據

- CLAUDE.md 與 rules：<https://code.claude.com/docs/en/memory>（200 行建議、CLAUDE.md 不具強制力、使用者層級規則、symlink 限制）
- Skills：<https://code.claude.com/docs/en/skills>（個人 skill 路徑、同名時個人優先於專案、1,536 字元上限、`${CLAUDE_SKILL_DIR}`）
