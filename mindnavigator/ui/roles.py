
from __future__ import annotations
from PySide6.QtCore import Qt

# Common
ROLE_ID = Qt.UserRole + 1
ROLE_KIND = Qt.UserRole + 2
ROLE_TITLE = Qt.UserRole + 3

# Notes
ROLE_CONTENT = Qt.UserRole + 61
ROLE_COVER_PATH = Qt.UserRole + 60
ROLE_FOLDER = Qt.UserRole + 62
ROLE_SOURCE_URL = Qt.UserRole + 63

# Files
ROLE_PARENT_ID = Qt.UserRole + 70
ROLE_IS_DIR = Qt.UserRole + 71
ROLE_LOCAL_PATH = Qt.UserRole + 75
ROLE_PREVIEW_PATH = Qt.UserRole + 76

# Maps
ROLE_MAP_ID = Qt.UserRole + 40
ROLE_X = Qt.UserRole + 41
ROLE_Y = Qt.UserRole + 42
ROLE_COLOR = Qt.UserRole + 11
ROLE_ICON = Qt.UserRole + 12
