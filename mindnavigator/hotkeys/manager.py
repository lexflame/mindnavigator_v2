from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import Conflict, HotkeyBinding, HotkeyCommand

_EDITING_SHORTCUTS = {
    "Ctrl+X",
    "Ctrl+C",
    "Ctrl+V",
    "Ctrl+Z",
    "Ctrl+Y",
    "Ctrl+A",
}

_CONTEXT_PRIORITY = {
    "ModalOnly": 0,
    "Widget": 1,
    "Workspace": 2,
    "Global": 3,
}


class HotkeyManager:
    def __init__(self, commands: Iterable[HotkeyCommand] | None = None):
        self._commands: dict[str, HotkeyCommand] = {}
        self._bindings: dict[str, HotkeyBinding] = {}
        self._active_contexts: list[str] = ["Global"]
        if commands:
            for command in commands:
                self.register_command(command)

    @property
    def commands(self) -> dict[str, HotkeyCommand]:
        return self._commands

    @property
    def bindings(self) -> dict[str, HotkeyBinding]:
        return self._bindings

    def register_command(self, command: HotkeyCommand) -> None:
        self._commands[command.id] = command
        if command.id not in self._bindings:
            self._bindings[command.id] = HotkeyBinding(
                command_id=command.id,
                sequence=normalize_sequence(command.default_sequence),
                enabled=True,
                user_defined=False,
            )

    def bind(self, command_id: str, sequence: str, user_defined: bool = True) -> None:
        self._require_command(command_id)
        self._bindings[command_id] = HotkeyBinding(
            command_id=command_id,
            sequence=normalize_sequence(sequence),
            enabled=True,
            user_defined=user_defined,
        )

    def unbind(self, command_id: str) -> None:
        command = self._require_command(command_id)
        self._bindings[command_id] = HotkeyBinding(
            command_id=command_id,
            sequence=normalize_sequence(command.default_sequence),
            enabled=True,
            user_defined=False,
        )

    def set_enabled(self, command_id: str, enabled: bool) -> None:
        self._require_command(command_id)
        binding = self._bindings[command_id]
        binding.enabled = enabled

    def set_active_contexts(self, contexts: list[str]) -> None:
        self._active_contexts = contexts or ["Global"]

    def resolve(
        self,
        sequence: str,
        focus_is_text_input: bool,
        active_contexts: list[str] | None = None,
    ) -> str | None:
        normalized_sequence = normalize_sequence(sequence)
        contexts = active_contexts if active_contexts is not None else self._active_contexts

        matches: list[tuple[int, str]] = []
        for command_id, command in self._commands.items():
            binding = self._bindings.get(command_id)
            if not binding or not binding.enabled:
                continue
            if binding.sequence != normalized_sequence:
                continue
            if not self._command_context_active(command, contexts):
                continue
            if focus_is_text_input and not command.allow_in_text_inputs and normalized_sequence in _EDITING_SHORTCUTS:
                continue
            matches.append((self._best_context_priority(command, contexts), command_id))

        if not matches:
            return None

        matches.sort(key=lambda item: item[0])
        top_priority = matches[0][0]
        top = [command_id for priority, command_id in matches if priority == top_priority]
        if len(top) > 1:
            return None
        return top[0]

    def detect_conflicts(self) -> list[Conflict]:
        conflicts: list[Conflict] = []
        by_key: dict[tuple[str, str], list[str]] = {}

        for command_id, command in self._commands.items():
            binding = self._bindings.get(command_id)
            if not binding or not binding.enabled:
                continue
            for context in command.contexts:
                group_context = context if context == "Global" or context == "ModalOnly" else context.split(":", 1)[0]
                by_key.setdefault((binding.sequence, group_context), []).append(command_id)

        for (sequence, context), command_ids in by_key.items():
            if len(command_ids) > 1:
                conflicts.append(
                    Conflict(
                        sequence=sequence,
                        context=context,
                        command_ids=tuple(sorted(command_ids)),
                        reason="multiple_commands_same_sequence_same_priority",
                    )
                )
        return conflicts

    def get_active_hotkeys(self, active_contexts: list[str] | None = None) -> list[tuple[HotkeyCommand, HotkeyBinding]]:
        contexts = active_contexts if active_contexts is not None else self._active_contexts
        result: list[tuple[HotkeyCommand, HotkeyBinding]] = []
        for command_id, command in self._commands.items():
            binding = self._bindings.get(command_id)
            if not binding or not binding.enabled:
                continue
            if self._command_context_active(command, contexts):
                result.append((command, binding))
        return sorted(result, key=lambda item: (self._best_context_priority(item[0], contexts), item[0].title.lower()))

    def _require_command(self, command_id: str) -> HotkeyCommand:
        if command_id not in self._commands:
            raise KeyError(f"Unknown command: {command_id}")
        return self._commands[command_id]

    def _best_context_priority(self, command: HotkeyCommand, active_contexts: list[str]) -> int:
        priorities: list[int] = []
        for context in command.contexts:
            if context == "Global":
                priorities.append(_CONTEXT_PRIORITY["Global"])
                continue
            if context == "ModalOnly" and "ModalOnly" in active_contexts:
                priorities.append(_CONTEXT_PRIORITY["ModalOnly"])
                continue
            if context.startswith("Widget:") and context in active_contexts:
                priorities.append(_CONTEXT_PRIORITY["Widget"])
                continue
            if context.startswith("Workspace:") and context in active_contexts:
                priorities.append(_CONTEXT_PRIORITY["Workspace"])
        return min(priorities) if priorities else 99

    def _command_context_active(self, command: HotkeyCommand, active_contexts: list[str]) -> bool:
        for context in command.contexts:
            if context == "Global":
                return True
            if context == "ModalOnly" and "ModalOnly" in active_contexts:
                return True
            if context.startswith("Widget:") and context in active_contexts:
                return True
            if context.startswith("Workspace:") and context in active_contexts:
                return True
        return False


class HotkeyOverridesStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, manager: HotkeyManager) -> None:
        payload: dict[str, dict] = {}
        for command_id, command in manager.commands.items():
            binding = manager.bindings[command_id]
            normalized_default = normalize_sequence(command.default_sequence)
            if binding.sequence != normalized_default or not binding.enabled:
                payload[command_id] = {
                    "sequence": binding.sequence,
                    "enabled": binding.enabled,
                }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def apply(self, manager: HotkeyManager) -> None:
        overrides = self.load()
        for command_id, value in overrides.items():
            if command_id not in manager.commands:
                continue
            manager.bind(command_id, value.get("sequence") or manager.commands[command_id].default_sequence, user_defined=True)
            manager.set_enabled(command_id, bool(value.get("enabled", True)))


def load_commands_from_json(path: Path) -> list[HotkeyCommand]:
    data = json.loads(path.read_text(encoding="utf-8"))
    commands: list[HotkeyCommand] = []
    for item in data.get("commands", []):
        commands.append(
            HotkeyCommand(
                id=item["id"],
                title=item["title"],
                description=item["description"],
                default_sequence=item["default_sequence"],
                contexts=item.get("contexts", ["Global"]),
                allow_in_text_inputs=bool(item.get("allow_in_text_inputs", False)),
            )
        )
    return commands


def normalize_sequence(sequence: str) -> str:
    tokens = [part.strip() for part in sequence.split("+") if part.strip()]
    modifiers: list[str] = []
    key: str | None = None
    for token in tokens:
        low = token.lower()
        if low in {"ctrl", "control"}:
            modifiers.append("Ctrl")
        elif low == "shift":
            modifiers.append("Shift")
        elif low in {"alt", "option"}:
            modifiers.append("Alt")
        elif low in {"meta", "cmd", "command", "win"}:
            modifiers.append("Meta")
        else:
            if len(token) == 1:
                key = token.upper()
            elif token == ",":
                key = ","
            else:
                key = token[0].upper() + token[1:]
    ordered_modifiers = []
    for mod in ("Ctrl", "Shift", "Alt", "Meta"):
        if mod in modifiers:
            ordered_modifiers.append(mod)
    if key is None:
        return "+".join(ordered_modifiers)
    return "+".join([*ordered_modifiers, key])
