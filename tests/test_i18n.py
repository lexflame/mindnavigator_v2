from __future__ import annotations

import mindnavigator.spaceenity.i18n as i18n


def test_normalize_language_code_falls_back_to_default() -> None:
    assert i18n.normalize_language_code("") == i18n.DEFAULT_LANGUAGE
    assert i18n.normalize_language_code("  EN  ") == "en"
    assert i18n.normalize_language_code("jp") == i18n.DEFAULT_LANGUAGE


def test_get_mode_labels_uses_selected_language() -> None:
    labels = i18n.get_mode_labels("de")

    assert labels[i18n.MODE_TASKS] == "Aufgaben"
    assert labels[i18n.MODE_CHARACTERS] == "Charaktere"
    assert labels[i18n.MODE_SETTINGS] == "Einstellungen"


def test_get_mode_label_returns_mode_key_for_unknown_mode() -> None:
    assert i18n.get_mode_label("UnknownMode", "fr") == "UnknownMode"
