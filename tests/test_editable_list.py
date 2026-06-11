from __future__ import annotations

from PySide6.QtWidgets import QApplication, QFrame, QLabel, QLineEdit, QToolButton

from mindnavigator.ui.editable_list import EditableListItem, EditableListWidget


def test_editable_list_builds_rows_and_emits_target_indices() -> None:
    _app = QApplication.instance() or QApplication([])
    widget = EditableListWidget(icon_color="#ffffff")
    edited: list[int] = []
    deleted: list[int] = []
    acted: list[int] = []
    widget.editRequested.connect(edited.append)
    widget.deleteRequested.connect(deleted.append)
    widget.actionRequested.connect(acted.append)

    widget.set_items(
        [
            EditableListItem("First"),
            EditableListItem("Second", action_icon="fa5s.check", action_tooltip="Toggle"),
        ]
    )

    inputs = widget.rows_widget.findChildren(QLineEdit)
    buttons = widget.rows_widget.findChildren(QToolButton)
    assert [item.text() for item in inputs] == ["First", "Second"]
    assert all(item.isReadOnly() for item in inputs)
    assert len(buttons) == 5

    buttons[2].click()
    buttons[3].click()
    buttons[4].click()

    assert edited == [1]
    assert acted == [1]
    assert deleted == [1]


def test_editable_list_add_and_edit_mode() -> None:
    _app = QApplication.instance() or QApplication([])
    widget = EditableListWidget(icon_color="#ffffff")
    added: list[bool] = []
    widget.addRequested.connect(lambda: added.append(True))

    widget.add_button.click()
    assert added == [True]

    widget.set_edit_enabled(False)
    assert all(button.isHidden() and not button.isEnabled() for button in widget.findChildren(QToolButton))


def test_editable_list_renders_optional_detail_and_color_marker() -> None:
    _app = QApplication.instance() or QApplication([])
    widget = EditableListWidget(icon_color="#ffffff")

    widget.set_items(
        [EditableListItem("Development", detail="DEV · High · Важность 5", marker_color="#20f5d2")]
    )

    detail = widget.rows_widget.findChild(QLabel, "EditableListDetail")
    marker = widget.rows_widget.findChild(QFrame, "EditableListMarker")
    assert detail is not None
    assert detail.text() == "DEV · High · Важность 5"
    assert marker is not None
    assert "#20f5d2" in marker.styleSheet()
