# claude-dotfiles

個人化的 Claude Code 設定：一份全域 CLAUDE.md，加上以 [Spec Kit](https://github.com/github/spec-kit) 進行規格驅動開發（SDD）的三個 skill。

| 內容 | 用途 |
|---|---|
| `home/CLAUDE.md` | 所有專案共用的工作偏好 |
| `/sdd-init` | 在專案導入最新穩定版 Spec Kit，或再移除 |
| `sdd-derive` | 從既有專案導出 constitution 與 spec |
| `sdd-grill` | 逐題追問，討論出 constitution 與 spec |

> **目前狀態**：只在 Linux 驗收過，Windows 尚未驗證。macOS 不在支援範圍。

## 安裝

需要 [uv](https://docs.astral.sh/uv/)、git 與 Claude Code。

在 repo 根目錄執行：

```text
git config user.email "<id>+<帳號>@users.noreply.github.com"
uv run tools/check_allowlist.py --install-hook
uv run tools/dotfiles.py deploy
```

前兩行每個 clone 都要做一次，它們會讓這個 repo 的 commit 不帶個人 email，並在 commit 前檢查內容。

第三行會把 `home/` 複製到 `~/.claude/`：

- 已有的 `CLAUDE.md` 會先備份，再被取代。
- 同名且不受管的 skill 會讓部署停止；確定要取代時加 `--force`，原內容同樣會先備份。
- 其他內容不受影響。

## 日常使用

依專案狀況選擇起點：

| 專案狀況 | 做法 |
|---|---|
| 還沒導入 Spec Kit | 手動執行 `/sdd-init`，它會提示下一步 |
| 新專案或方向未定 | 請 Claude 追問討論，會使用 `sdd-grill` |
| 已有程式碼 | 請 Claude 導出 constitution 與 spec，會使用 `sdd-derive` |

`sdd-grill` 與 `sdd-derive` 都會先等你確認，才寫入文件，並且止於 spec。之後用 Spec Kit 接續：

```text
/speckit-plan → /speckit-tasks → /speckit-implement
```

多個功能時，每個功能各跑一次。Spec Kit 用 `.specify/feature.json` 決定目前處理哪個功能，切換 git 分支不會跟著切換，要換功能時請修改：

```json
{ "feature_directory": "specs/002-example" }
```

`sdd-grill` 中斷後再次執行，可以選擇接續或重新開始。進度存在專案的 `.specify/sdd-grill-progress.md`，不會入庫，所以無法換機器接續。

從專案移除 Spec Kit：

```text
/sdd-init remove        # 刪除未修改的檔案，已修改的保留並回報
/sdd-init remove --all  # 連已修改的檔案一併刪除
```

兩者都不會動 `specs/` 與 `.git`。

## 維護

部署是複製檔案，所以修改 `home/` 後要重新部署。

| 指令 | 用途 |
|---|---|
| `uv run tools/dotfiles.py status` | 查看部署狀態 |
| `uv run tools/dotfiles.py deploy` | 部署或更新，重複執行不會有變更 |
| `uv run tools/dotfiles.py undeploy` | 還原到部署前的狀態 |
| `uv run -m unittest discover -s tests` | 執行測試 |
| `uv run tools/run_trigger_evals.py` | 檢查 skill 是否正確觸發；會呼叫模型並產生費用 |

`status` 的結果：

| 狀態 | 意思 | 處理方式 |
|---|---|---|
| `not-deployed` | 尚未部署 | 執行 `deploy` |
| `clean` | 本機與 repo 相同 | 不用處理 |
| `repo-ahead` | `home/` 有更新 | 執行 `deploy` |
| `local-modified` | `~/.claude/` 內的受管檔案被改過 | 把想保留的改動移到 `home/`，再執行 `deploy`；本機改動會先另存備份 |
| `incomplete` | 上次部署中斷 | 執行 `deploy` 或 `undeploy` |

機器專屬的內容放在 `~/.claude/rules/`，部署不會碰這個目錄，也不會入庫。

要加入新的 skill，請見 [docs/adding-a-skill.md](docs/adding-a-skill.md)。新增其他路徑的檔案前，要先加進 `.repo-allowlist`，否則 commit 會被擋下。

## 已知限制

- **尚未公開就緒**：commit 檢查不看 commit 訊息與歷史，也能被 `--no-verify` 略過。完整防護由 `specs/001-repo-commit-guard` 負責，完成前不要公開這個 repo。
- **`core.hooksPath`**：有設定時，要確認它會轉交給 `.git/hooks`，否則 commit 檢查不會執行。
- **模型差異**：Sonnet 的驗收全部通過。Haiku 曾用英文回覆英文提問，也較容易忽略 skill 的收尾步驟與「不加未確認規則」的指示。
- **一個專案只有一種 Spec Kit 腳本**：Windows 導入的用 PowerShell，Linux 導入的用 bash。專案換到另一個作業系統時，需要對應的 shell。
- **最新版可能不相容**：`/sdd-init` 一律安裝最新穩定版，不同時間的新專案可能拿到不同版本。Spec Kit 改版造成不相容時，skill 會回報並停止。

## 開發規則

這個 repo 本身也用 SDD 開發。開發規則見 [constitution](.specify/memory/constitution.md)，功能規格見 [specs/](specs/)。
