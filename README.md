# MindNavigator (TasksWorkspace + ProjectsWorkspace (UI-only), split files)

## Requirements
- Python 3.10+
- PySide6
- qtawesome (`pip install qtawesome`)

## Run
```bash
python main.py
```

Ensure `assets/` exists next to `main.py`:
- assets/icon.png
- assets/splash.png


## Data storage
This version stores Projects/Tasks in SQLite: `data/mindnavigator.db` (auto-created + seeded on first run).
