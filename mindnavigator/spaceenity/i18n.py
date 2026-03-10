"""Runtime i18n helpers for shell-level UI labels."""

from __future__ import annotations

DEFAULT_LANGUAGE = "ru"

SUPPORTED_LANGUAGES: dict[str, str] = {
    "ru": "\u0420\u0443\u0441\u0441\u043a\u0438\u0439",
    "en": "English",
    "de": "Deutsch",
    "fr": "Fran\u00e7ais",
    "zh": "\u4e2d\u6587",
}

MODE_PROJECTS = "\u041f\u0440\u043e\u0435\u043a\u0442\u044b"
MODE_TASKS = "\u0417\u0430\u0434\u0430\u0447\u0438"
MODE_PURCHASES = "\u041f\u043e\u043a\u0443\u043f\u043a\u0438"
MODE_IDEAS = "\u0418\u0434\u0435\u0438"
MODE_COLLECTIONS = "\u041a\u043e\u043b\u043b\u0435\u043a\u0446\u0438\u0438"
MODE_MAPS = "\u041a\u0430\u0440\u0442\u044b"
MODE_NOTES = "\u0417\u0430\u043c\u0435\u0442\u043a\u0438"
MODE_FILES = "\u0424\u0430\u0439\u043b\u044b"
MODE_OBJECTS = "\u041e\u0431\u044a\u0435\u043a\u0442\u044b"
MODE_CHARACTERS = "\u041f\u0435\u0440\u0441\u043e\u043d\u0430\u0436\u0438"
MODE_MINDDRAW = "MindDraw"
MODE_SETTINGS = "\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438"

_MODE_LABELS: dict[str, dict[str, str]] = {
    "ru": {
        MODE_PROJECTS: MODE_PROJECTS,
        MODE_TASKS: MODE_TASKS,
        MODE_PURCHASES: MODE_PURCHASES,
        MODE_IDEAS: MODE_IDEAS,
        MODE_COLLECTIONS: MODE_COLLECTIONS,
        MODE_MAPS: MODE_MAPS,
        MODE_NOTES: MODE_NOTES,
        MODE_FILES: MODE_FILES,
        MODE_OBJECTS: MODE_OBJECTS,
        MODE_CHARACTERS: MODE_CHARACTERS,
        MODE_MINDDRAW: MODE_MINDDRAW,
        MODE_SETTINGS: MODE_SETTINGS,
    },
    "en": {
        MODE_PROJECTS: "Projects",
        MODE_TASKS: "Tasks",
        MODE_PURCHASES: "Purchases",
        MODE_IDEAS: "Ideas",
        MODE_COLLECTIONS: "Collections",
        MODE_MAPS: "Maps",
        MODE_NOTES: "Notes",
        MODE_FILES: "Files",
        MODE_OBJECTS: "Objects",
        MODE_CHARACTERS: "Characters",
        MODE_MINDDRAW: "MindDraw",
        MODE_SETTINGS: "Settings",
    },
    "de": {
        MODE_PROJECTS: "Projekte",
        MODE_TASKS: "Aufgaben",
        MODE_PURCHASES: "Einkäufe",
        MODE_IDEAS: "Ideen",
        MODE_COLLECTIONS: "Sammlungen",
        MODE_MAPS: "Karten",
        MODE_NOTES: "Notizen",
        MODE_FILES: "Dateien",
        MODE_OBJECTS: "Objekte",
        MODE_CHARACTERS: "Charaktere",
        MODE_MINDDRAW: "MindDraw",
        MODE_SETTINGS: "Einstellungen",
    },
    "fr": {
        MODE_PROJECTS: "Projets",
        MODE_TASKS: "Tâches",
        MODE_PURCHASES: "Achats",
        MODE_IDEAS: "Idées",
        MODE_COLLECTIONS: "Collections",
        MODE_MAPS: "Cartes",
        MODE_NOTES: "Notes",
        MODE_FILES: "Fichiers",
        MODE_OBJECTS: "Objets",
        MODE_CHARACTERS: "Personnages",
        MODE_MINDDRAW: "MindDraw",
        MODE_SETTINGS: "Paramètres",
    },
    "zh": {
        MODE_PROJECTS: "\u9879\u76ee",
        MODE_TASKS: "\u4efb\u52a1",
        MODE_PURCHASES: "\u8d2d\u7269",
        MODE_IDEAS: "\u60f3\u6cd5",
        MODE_COLLECTIONS: "\u6536\u85cf",
        MODE_MAPS: "\u5730\u56fe",
        MODE_NOTES: "\u7b14\u8bb0",
        MODE_FILES: "\u6587\u4ef6",
        MODE_OBJECTS: "\u5bf9\u8c61",
        MODE_CHARACTERS: "\u89d2\u8272",
        MODE_MINDDRAW: "MindDraw",
        MODE_SETTINGS: "\u8bbe\u7f6e",
    },
}


def normalize_language_code(language_code: str) -> str:
    code = (language_code or "").strip().lower()
    return code if code in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def get_mode_label(mode_key: str, language_code: str) -> str:
    labels = get_mode_labels(language_code)
    return labels.get(mode_key, mode_key)


def get_mode_labels(language_code: str) -> dict[str, str]:
    code = normalize_language_code(language_code)
    labels = _MODE_LABELS.get(code) or _MODE_LABELS[DEFAULT_LANGUAGE]
    return dict(labels)
