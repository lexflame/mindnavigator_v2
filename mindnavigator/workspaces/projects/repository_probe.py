"""RepositoryProbe class module for projects workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class RepositoryProbe:
    def inspect(self, repository_catalog: str) -> RepositoryProbeState:
        repo_path = (repository_catalog or "").strip()
        if not repo_path:
            return RepositoryProbeState(False, message="Каталог репозитория не указан.")
        path = Path(repo_path)
        if not path.exists() or not path.is_dir():
            return RepositoryProbeState(False, message="Каталог репозитория не найден.")
        try:
            branch_proc = subprocess.run(
                ["git", "-C", str(path), "rev-parse", "--abbrev-ref", "HEAD"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return RepositoryProbeState(False, message=str(exc))
        if branch_proc.returncode != 0:
            error_text = (branch_proc.stderr or "").strip() or "Невозможно определить ветку репозитория."
            return RepositoryProbeState(False, message=error_text)
        branch_name = (branch_proc.stdout or "").strip() or "(detached)"
        try:
            status_proc = subprocess.run(
                ["git", "-C", str(path), "status", "--porcelain"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return RepositoryProbeState(False, message=str(exc))
        if status_proc.returncode != 0:
            error_text = (status_proc.stderr or "").strip() or "Невозможно получить состояние репозитория."
            return RepositoryProbeState(False, message=error_text)
        has_changes = bool((status_proc.stdout or "").strip())
        return RepositoryProbeState(True, branch_name=branch_name, has_local_changes=has_changes)

__all__ = ["RepositoryProbe"]
