from pathlib import Path

import mindnavigator.workspaces.settings.settings_workspace as settings_workspace
from mindnavigator.workspaces.settings import SettingsWorkspace


def test_autostart_command_uses_packaged_executable(monkeypatch) -> None:
    executable = Path("C:/Program Files/MindNavigator/MindNavigator.exe")
    monkeypatch.setattr(settings_workspace.sys, "frozen", True, raising=False)
    monkeypatch.setattr(settings_workspace.sys, "executable", str(executable))

    assert SettingsWorkspace._autostart_command() == f'"{executable}"'


def test_autostart_command_uses_windowed_python_launcher(monkeypatch, tmp_path) -> None:
    python_executable = tmp_path / "python.exe"
    python_executable.touch()
    pythonw_executable = tmp_path / "pythonw.exe"
    pythonw_executable.touch()
    monkeypatch.setattr(settings_workspace.sys, "frozen", False, raising=False)
    monkeypatch.setattr(settings_workspace.sys, "executable", str(python_executable))

    command = SettingsWorkspace._autostart_command()

    assert command.startswith(f'"{pythonw_executable}" ')
    expected_main = Path(settings_workspace.__file__).resolve().parents[3] / "main.py"
    assert command.endswith(f'"{expected_main}"')


def test_autostart_command_falls_back_when_pythonw_is_missing(monkeypatch, tmp_path) -> None:
    python_executable = tmp_path / "python.exe"
    python_executable.touch()
    monkeypatch.setattr(settings_workspace.sys, "frozen", False, raising=False)
    monkeypatch.setattr(settings_workspace.sys, "executable", str(python_executable))

    command = SettingsWorkspace._autostart_command()

    assert command.startswith(f'"{python_executable}" ')
