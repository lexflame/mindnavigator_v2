"""Helpers for applying versioned SQLite schema migrations."""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from typing import Callable, Sequence


MigrationCallable = Callable[[sqlite3.Connection], None]


@dataclass(frozen=True)
class MigrationStep:
    """Single schema migration step bound to a target `user_version`."""

    version: int
    name: str
    apply: MigrationCallable


def get_user_version(connection: sqlite3.Connection) -> int:
    """Read current SQLite schema version from PRAGMA user_version."""
    row = connection.execute("PRAGMA user_version;").fetchone()
    return int(row[0]) if row else 0


def set_user_version(connection: sqlite3.Connection, version: int) -> None:
    """Write SQLite schema version to PRAGMA user_version."""
    connection.execute(f"PRAGMA user_version = {int(version)};")


def apply_migrations(connection: sqlite3.Connection, steps: Sequence[MigrationStep]) -> int:
    """Apply all migration steps with version greater than current user_version."""
    ordered = sorted(steps, key=lambda migration_step: migration_step.version)
    seen_versions: set[int] = set()
    for step in ordered:
        if step.version < 1:
            raise ValueError(f"Migration '{step.name}' has invalid version: {step.version}")
        if step.version in seen_versions:
            raise ValueError(f"Duplicate migration version detected: {step.version}")
        seen_versions.add(step.version)

    current_version = get_user_version(connection)
    for step in ordered:
        if step.version <= current_version:
            continue
        with connection:
            step.apply(connection)
            set_user_version(connection, step.version)
        current_version = step.version
    return current_version
