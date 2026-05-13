# COMMANDS.md

## Navigation
- Find files: `rg --files`
- Find symbol or text: `rg -n "<pattern>" mindnavigator tests`
- Find references across docs and config: `rg -n "<pattern>" .codex docs`

## Validation
- Syntax check: `python -m compileall mindnavigator main.py`
- Focused tests: `PYTHONPATH=. pytest tests -k <scope>`
- Full tests (env-safe): `PYTHONPATH=. pytest tests -p no:cacheprovider --basetemp .pytest_dir/run_tmp`
- Full tests (headless Qt): `PYTHONPATH=. QT_QPA_PLATFORM=offscreen pytest tests -p no:cacheprovider --basetemp .pytest_dir/run_tmp`

## Build Triggers
- `b_start`: build + compile + place into `C:\Program Portable\MindNavigator\` + run
- `b_build`: build + compile + place into `C:\Program Portable\MindNavigator\` (without run)

## Git Hygiene
- Current branch: `git branch --show-current`
- Status: `git status --short`
- Branch status: `git status --short --branch`
- Diff summary: `git diff --stat`
- Changed files: `git diff --name-only`
- Last commit: `git log -1 --stat`
- Create task branch: `git switch -c codex/<task>` or `git switch -c feature/<task>`
- Push task branch: `git push --set-upstream origin <branch>`
- Create PR: `gh pr create --base <base-branch> --head <branch> --title "<title>" --body "<body>"`

## Sprint Delivery
- Create sprint branch: `git switch -c sprint/<id_or_topic>`
- Create partition branch: `git switch -c sprint/<id_or_topic>-p<partition>`
- Push current branch: `git push -u origin <branch>`
- Fast-forward local main: `git fetch origin main` then `git merge --ff-only origin/main`

## History Helpers
- Find task history: `rg -n "<TASK_GUID>" .codex/HISTORY_TASK.md .codex/HISTORY_ACTION.md`
- Append action line format: `[YYYY-MM-DD HH:MM] ACTION: <message>`
- Append command line format: `[YYYY-MM-DD HH:MM] CMD: <command>`
- Append command result format: `[YYYY-MM-DD HH:MM] OUT: <meaningful result>`

## Reporting Template
- Changed:
- Validation:
- Risks:
- Next step:
