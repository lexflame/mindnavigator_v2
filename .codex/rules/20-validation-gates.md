# Validation Gates Rule

## Minimum Before Final Response
- Run `python -m compileall mindnavigator main.py` for code changes.
- Run `PYTHONPATH=. pytest tests -k <changed_scope>` for changed behavior.
- If tests were not run, explain why.

## Conditional Gates
- If storage schema changed, validate migration and read/write paths together.
- If UI behavior changed, validate affected interaction path (test or manual check).

## Reporting
- Report executed validation commands and outcomes.
- Report residual risks explicitly.
