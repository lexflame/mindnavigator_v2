from __future__ import annotations

from PySide6.QtWidgets import QApplication

from mindnavigator.ui import search_nav


class _DummyDb:
    pass


def _create_widget(monkeypatch) -> search_nav.SearchNav:
    _app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(search_nav, "get_database", lambda: _DummyDb())
    return search_nav.SearchNav()


def test_search_nav_debounces_non_empty_queries(monkeypatch) -> None:
    widget = _create_widget(monkeypatch)
    queries: list[str] = []
    monkeypatch.setattr(widget, "_collect_matches", lambda query: queries.append(query) or [])

    widget.input.setText("pro")
    widget.input.setText("project")

    assert widget._search_timer.isSingleShot()
    assert widget._search_timer.interval() == 200
    assert widget._search_timer.isActive()
    assert queries == []

    widget._search_timer.timeout.emit()
    widget._search_timer.stop()

    assert queries == ["project"]


def test_search_nav_clears_immediately_and_cancels_pending_search(monkeypatch) -> None:
    widget = _create_widget(monkeypatch)
    queries: list[str] = []
    monkeypatch.setattr(widget, "_collect_matches", lambda query: queries.append(query) or [])

    widget.input.setText("task")
    assert widget._search_timer.isActive()

    widget.input.clear()

    assert not widget._search_timer.isActive()
    assert queries == []
    assert not widget.results_placeholder.isHidden()
    assert widget.results_list.isHidden()
