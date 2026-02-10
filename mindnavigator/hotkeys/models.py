from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HotkeyCommand:
    id: str
    title: str
    description: str
    default_sequence: str
    contexts: list[str]
    allow_in_text_inputs: bool = False


@dataclass
class HotkeyBinding:
    command_id: str
    sequence: str
    enabled: bool = True
    user_defined: bool = False


@dataclass(frozen=True)
class Conflict:
    sequence: str
    context: str
    command_ids: tuple[str, ...]
    reason: str
