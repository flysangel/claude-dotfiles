# 加入新的 skill

1. **確認需求來源。** 來源要是實際遇到的需求，或維護者的明確要求，並寫進 commit message。不要為假設的未來需求預先加入。
2. **確認機制。** 按需流程才用 skill；必須強制的放 hook 或 settings，每次都適用的偏好放 `home/CLAUDE.md`。
3. **新增 skill。** 建立 `home/skills/<name>/SKILL.md`。frontmatter 的 `name` 要與目錄同名，`description` 要說明做什麼與何時使用。有副作用、要自己掌握時機的流程，設定 `disable-model-invocation: true`。
4. **新增驗收檔案。** 建立 `tests/skills/<name>/` 的兩個檔案：
   - `triggers.json`：`should_trigger` 與 `should_not_trigger` 提示。只能手動執行的 skill，`should_trigger` 留空。
   - `scenarios.md`：操作與預期結果。
5. **執行測試。** `uv run -m unittest discover -s tests`。
6. **驗收。** 把 skill 複製到暫存專案的 `.claude/skills/`，依 `scenarios.md` 操作。
7. **檢查觸發。** `uv run tools/run_trigger_evals.py <name>`。這會呼叫模型並產生費用。
8. **部署。** `uv run tools/dotfiles.py deploy`。
