from typing import TYPE_CHECKING

from .manager import HotkeyManager, HotkeyOverridesStore, load_commands_from_json, normalize_sequence
from .models import Conflict, HotkeyBinding, HotkeyCommand

if TYPE_CHECKING:
    from .event_filter import HotkeyEventFilter, is_editable_widget

__all__ = [
    "Conflict",
    "HotkeyBinding",
    "HotkeyCommand",
    "HotkeyEventFilter",
    "HotkeyManager",
    "HotkeyOverridesStore",
    "is_editable_widget",
    "load_commands_from_json",
    "normalize_sequence",
]


def __getattr__(name: str):
    if name in {"HotkeyEventFilter", "is_editable_widget"}:
        from .event_filter import HotkeyEventFilter, is_editable_widget

        if name == "HotkeyEventFilter":
            return HotkeyEventFilter
        return is_editable_widget
    raise AttributeError(name)
