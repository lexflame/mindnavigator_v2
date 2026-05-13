from __future__ import annotations

from PySide6.QtWidgets import QApplication, QLineEdit, QMenu, QPlainTextEdit, QTextEdit, QVBoxLayout, QWidget

from mindnavigator.ui.spellcheck import GlobalSpellCheckService, SpellCheckIssue, iter_spellcheck_tokens


class _FakeSpellBackend:
    def __init__(self) -> None:
        self.ignored: set[str] = set()

    @property
    def enabled(self) -> bool:
        return True

    def analyze_text(self, text: str) -> list[SpellCheckIssue]:
        if "teh" in self.ignored:
            return []
        issues: list[SpellCheckIssue] = []
        start = text.find("teh")
        while start >= 0:
            issues.append(
                SpellCheckIssue(
                    start=start,
                    length=3,
                    word="teh",
                    suggestions=("the",),
                )
            )
            start = text.find("teh", start + 3)
        return issues

    def ignore_word(self, word: str) -> None:
        self.ignored.add(word.casefold())


def test_iter_spellcheck_tokens_finds_words_and_keeps_hyphenated_forms() -> None:
    tokens = [match.group(0) for match in iter_spellcheck_tokens("alpha beta-test ёлка")]
    assert tokens == ["alpha", "beta-test", "ёлка"]


def test_spellcheck_service_attaches_to_editable_text_inputs() -> None:
    _app = QApplication.instance() or QApplication([])
    backend = _FakeSpellBackend()
    service = GlobalSpellCheckService(_app, backend=backend, check_delay_ms=0)

    root = QWidget()
    layout = QVBoxLayout(root)
    line_edit = QLineEdit()
    plain_edit = QPlainTextEdit()
    rich_edit = QTextEdit()
    search_edit = QLineEdit()
    search_edit.setObjectName("WorkspaceSearchInput")
    layout.addWidget(line_edit)
    layout.addWidget(plain_edit)
    layout.addWidget(rich_edit)
    layout.addWidget(search_edit)

    service.attach_widget_tree(root)

    assert service._controller_for_widget(line_edit) is not None
    assert service._controller_for_widget(plain_edit) is not None
    assert service._controller_for_widget(rich_edit) is not None
    assert service._controller_for_widget(search_edit) is None


def test_spellcheck_service_marks_and_replaces_misspellings() -> None:
    _app = QApplication.instance() or QApplication([])
    backend = _FakeSpellBackend()
    service = GlobalSpellCheckService(_app, backend=backend, check_delay_ms=0)

    root = QWidget()
    layout = QVBoxLayout(root)
    line_edit = QLineEdit()
    plain_edit = QPlainTextEdit()
    layout.addWidget(line_edit)
    layout.addWidget(plain_edit)
    service.attach_widget_tree(root)

    line_edit.setText("teh title")
    plain_edit.setPlainText("teh body")
    _app.processEvents()

    line_controller = service._controller_for_widget(line_edit)
    plain_controller = service._controller_for_widget(plain_edit)
    assert line_controller is not None
    assert plain_controller is not None
    assert len(line_controller.issues) == 1
    assert len(plain_controller.issues) == 1
    assert len(plain_edit.extraSelections()) == 1

    line_controller.replace_issue(line_controller.issues[0], "the")
    plain_controller.replace_issue(plain_controller.issues[0], "the")

    assert line_edit.text() == "the title"
    assert plain_edit.toPlainText() == "the body"


def test_spellcheck_service_can_ignore_word_for_session() -> None:
    _app = QApplication.instance() or QApplication([])
    backend = _FakeSpellBackend()
    service = GlobalSpellCheckService(_app, backend=backend, check_delay_ms=0)

    line_edit = QLineEdit()
    service.attach_widget_tree(line_edit)
    line_edit.setText("teh")
    _app.processEvents()

    controller = service._controller_for_widget(line_edit)
    assert controller is not None
    assert len(controller.issues) == 1

    controller.ignore_word("teh")

    assert controller.issues == []


def test_spellcheck_service_builds_spelling_submenu() -> None:
    _app = QApplication.instance() or QApplication([])
    backend = _FakeSpellBackend()
    service = GlobalSpellCheckService(_app, backend=backend, check_delay_ms=0)

    line_edit = QLineEdit()
    service.attach_widget_tree(line_edit)
    controller = service._controller_for_widget(line_edit)
    assert controller is not None

    menu = QMenu()
    first_standard_action = menu.addAction("Cut")
    issue = SpellCheckIssue(start=0, length=3, word="teh", suggestions=("the", "ten"))

    spelling_action = service._insert_spelling_submenu(menu, first_standard_action, controller, issue)

    assert spelling_action.text() == "Проверка орфографии"
    spelling_menu = spelling_action.menu()
    assert spelling_menu is not None
    assert [action.text() for action in spelling_menu.actions() if not action.isSeparator()] == [
        "the",
        "ten",
        "Игнорировать слово",
    ]
