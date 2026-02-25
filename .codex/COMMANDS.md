# COMMANDS.md

## Navigation
- Find files: `rg --files`
- Find symbol/text: `rg -n "<pattern>" mindnavigator tests`

## Validation
- Syntax check: `python -m compileall mindnavigator main.py`
- Focused tests: `pytest tests -k <scope>`
- Full tests (env-safe): `PYTHONPATH=. pytest tests -p no:cacheprovider --basetemp .pytest_dir/run_tmp`

## Build Triggers
- `b_start`: build + compile + run from project workspace `D:\_Branch\PROJECTS\project_work\mindnavigator\mindnavigator_v2\`
- `b_build`: build + compile in project workspace `D:\_Branch\PROJECTS\project_work\mindnavigator\mindnavigator_v2\` (without run)

## Git Hygiene
- Status: `git status --short`
- Diff summary: `git diff --stat`
- Changed files: `git diff --name-only`

## Reporting Template
- Changed:
- Validation:
- Risks:
- Next step:
