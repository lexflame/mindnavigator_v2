# Validation Gates Rule

- Before final response run:
  - `python -m compileall mindnavigator main.py`
  - `pytest tests -k <changed_scope>` (or explain why not run)
- If storage schema is changed, verify migration and read/write paths together.
- Report residual risks explicitly.
