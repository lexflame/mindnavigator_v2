from __future__ import annotations

from dataclasses import dataclass
import ctypes
import re
import sys
import uuid
from typing import Protocol, Sequence, cast

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QTimer, Qt
from PySide6.QtGui import QColor, QContextMenuEvent, QPainter, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QApplication, QLineEdit, QMenu, QPlainTextEdit, QTextEdit, QWidget

_WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё]+(?:[-'][A-Za-zА-Яа-яЁё]+)*")
_CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
_LATIN_RE = re.compile(r"[A-Za-z]")
_SKIP_NAME_HINTS = ("search", "url", "path", "file", "backup", "database", "db")
_SKIP_PLACEHOLDER_HINTS = ("search", "поиск", "url", "path", "путь", "файл", "file")
_SPELLCHECK_COLOR = QColor("#d64545")

_S_OK = 0
_S_FALSE = 1
_CLSCTX_INPROC_SERVER = 1
_COINIT_APARTMENTTHREADED = 0x2
_RPC_E_CHANGED_MODE = -2147417850


@dataclass(frozen=True)
class SpellCheckIssue:
    start: int
    length: int
    word: str
    suggestions: tuple[str, ...]


class _SpellCheckBackend(Protocol):
    @property
    def enabled(self) -> bool:
        ...

    def analyze_text(self, text: str) -> list[SpellCheckIssue]:
        ...

    def ignore_word(self, word: str) -> None:
        ...


class _NullSpellCheckBackend:
    @property
    def enabled(self) -> bool:
        return False

    def analyze_text(self, text: str) -> list[SpellCheckIssue]:
        return []

    def ignore_word(self, word: str) -> None:
        return None


class _Guid(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def _guid_from_string(value: str) -> _Guid:
    parsed = uuid.UUID(value)
    return _Guid(
        parsed.time_low,
        parsed.time_mid,
        parsed.time_hi_version,
        (ctypes.c_ubyte * 8)(
            parsed.clock_seq_hi_variant,
            parsed.clock_seq_low,
            *parsed.node.to_bytes(6, byteorder="big"),
        ),
    )


class _WindowsSpellCheckBackend:
    _CLSID_SPELLCHECKER_FACTORY = _guid_from_string("7AB36653-1796-484B-BDFA-E74F1DB7C1DC")
    _IID_ISPELLCHECKER_FACTORY = _guid_from_string("8E018A9D-2415-4677-BF08-794EA61F94BB")
    _PREFERRED_LANGUAGE_TAGS = ("ru-RU", "en-US", "en-GB")

    def __init__(self) -> None:
        self._ole32 = None
        self._factory = ctypes.c_void_p()
        self._checkers: dict[str, ctypes.c_void_p | None] = {}
        self._cache: dict[str, tuple[bool, tuple[str, ...]] | None] = {}
        self._ignored_words: set[str] = set()
        self._enabled = False
        if sys.platform != "win32":
            return
        try:
            ole32 = ctypes.OleDLL("ole32")
            ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            ole32.CoInitializeEx.restype = ctypes.c_long
            ole32.CoCreateInstance.argtypes = [
                ctypes.POINTER(_Guid),
                ctypes.c_void_p,
                ctypes.c_ulong,
                ctypes.POINTER(_Guid),
                ctypes.POINTER(ctypes.c_void_p),
            ]
            ole32.CoCreateInstance.restype = ctypes.c_long
            ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
            ole32.CoTaskMemFree.restype = None
            hr = int(ole32.CoInitializeEx(None, _COINIT_APARTMENTTHREADED))
            if hr not in (_S_OK, _S_FALSE, _RPC_E_CHANGED_MODE):
                return
            factory = ctypes.c_void_p()
            hr = int(
                ole32.CoCreateInstance(
                    ctypes.byref(self._CLSID_SPELLCHECKER_FACTORY),
                    None,
                    _CLSCTX_INPROC_SERVER,
                    ctypes.byref(self._IID_ISPELLCHECKER_FACTORY),
                    ctypes.byref(factory),
                )
            )
            if hr < 0 or not factory.value:
                return
            self._ole32 = ole32
            self._factory = factory
            self._enabled = any(self._ensure_checker(tag) is not None for tag in self._PREFERRED_LANGUAGE_TAGS)
        except OSError:
            self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def analyze_text(self, text: str) -> list[SpellCheckIssue]:
        if not self._enabled or not text:
            return []
        issues: list[SpellCheckIssue] = []
        for match in iter_spellcheck_tokens(text):
            word = match.group(0)
            if not _should_check_word(word):
                continue
            lowered = word.casefold()
            if lowered in self._ignored_words:
                continue
            cached = self._cache.get(lowered, None)
            if cached is None and lowered not in self._cache:
                cached = self._analyze_word(word)
                self._cache[lowered] = cached
            if cached is None:
                continue
            is_correct, suggestions = cached
            if is_correct:
                continue
            issues.append(
                SpellCheckIssue(
                    start=match.start(),
                    length=match.end() - match.start(),
                    word=word,
                    suggestions=suggestions,
                )
            )
        return issues

    def ignore_word(self, word: str) -> None:
        lowered = word.casefold()
        self._ignored_words.add(lowered)
        self._cache[lowered] = (True, tuple())
        for checker in self._checkers.values():
            if checker is None or not checker.value:
                continue
            ignore = self._com_method(checker, 7, ctypes.c_long, ctypes.c_wchar_p)
            ignore(checker, word)

    def _analyze_word(self, word: str) -> tuple[bool, tuple[str, ...]] | None:
        tags = _candidate_language_tags(word)
        if not tags:
            return None
        attempted = False
        miss_suggestions: tuple[str, ...] = tuple()
        for tag in tags:
            checker = self._ensure_checker(tag)
            if checker is None:
                continue
            attempted = True
            result = self._suggest_word(checker, word)
            if result is None:
                continue
            is_correct, suggestions = result
            if is_correct:
                return True, tuple()
            if not miss_suggestions:
                miss_suggestions = suggestions
        if not attempted:
            return None
        return False, miss_suggestions

    def _ensure_checker(self, language_tag: str) -> ctypes.c_void_p | None:
        if language_tag in self._checkers:
            return self._checkers[language_tag]
        if not self._factory.value:
            self._checkers[language_tag] = None
            return None
        create = self._com_method(self._factory, 5, ctypes.c_long, ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_void_p))
        checker = ctypes.c_void_p()
        hr = int(create(self._factory, language_tag, ctypes.byref(checker)))
        if hr < 0 or not checker.value:
            self._checkers[language_tag] = None
            return None
        self._checkers[language_tag] = checker
        return checker

    def _suggest_word(self, checker: ctypes.c_void_p, word: str) -> tuple[bool, tuple[str, ...]] | None:
        suggest = self._com_method(checker, 5, ctypes.c_long, ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_void_p))
        suggestions_enum = ctypes.c_void_p()
        hr = int(suggest(checker, word, ctypes.byref(suggestions_enum)))
        if hr < 0:
            return None
        suggestions = tuple(_normalize_suggestions(self._read_enum_strings(suggestions_enum), word))
        if hr == _S_FALSE:
            return True, tuple()
        return False, suggestions

    def _read_enum_strings(self, enum_interface: ctypes.c_void_p) -> list[str]:
        if not enum_interface.value:
            return []
        values: list[str] = []
        next_item = self._com_method(
            enum_interface,
            3,
            ctypes.c_long,
            ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_wchar_p),
            ctypes.POINTER(ctypes.c_ulong),
        )
        try:
            while True:
                fetched = ctypes.c_ulong()
                item = ctypes.c_wchar_p()
                hr = int(next_item(enum_interface, 1, ctypes.byref(item), ctypes.byref(fetched)))
                if fetched.value == 0:
                    break
                if item.value:
                    values.append(item.value)
                    if self._ole32 is not None:
                        self._ole32.CoTaskMemFree(ctypes.cast(item, ctypes.c_void_p))
                if hr not in (_S_OK, _S_FALSE):
                    break
        finally:
            self._release(enum_interface)
        return values

    @staticmethod
    def _com_method(interface: ctypes.c_void_p, index: int, restype, *argtypes):
        vtbl = ctypes.cast(interface, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        return ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(vtbl[index])

    @staticmethod
    def _release(interface: ctypes.c_void_p) -> None:
        if not interface.value:
            return
        vtbl = ctypes.cast(interface, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtbl[2])
        release(interface)


def _build_spellcheck_backend() -> _SpellCheckBackend:
    backend = _WindowsSpellCheckBackend()
    if backend.enabled:
        return backend
    return _NullSpellCheckBackend()


def iter_spellcheck_tokens(text: str):
    return _WORD_RE.finditer(text or "")


def _candidate_language_tags(word: str) -> tuple[str, ...]:
    has_cyrillic = bool(_CYRILLIC_RE.search(word))
    has_latin = bool(_LATIN_RE.search(word))
    if has_cyrillic and has_latin:
        return tuple()
    if has_cyrillic:
        return ("ru-RU", "en-US")
    if has_latin:
        return ("en-US", "en-GB")
    return tuple()


def _normalize_suggestions(suggestions: Sequence[str], word: str) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    word_key = word.casefold()
    for item in suggestions:
        candidate = str(item or "").strip()
        if not candidate:
            continue
        key = candidate.casefold()
        if key == word_key or key in seen:
            continue
        seen.add(key)
        normalized.append(candidate)
        if len(normalized) >= 6:
            break
    return normalized


def _should_check_word(word: str) -> bool:
    if len(word) < 3:
        return False
    if word.isupper() and len(word) <= 5:
        return False
    if word.casefold().startswith(("http", "www")):
        return False
    return True


def _should_attach_spellcheck(widget: QWidget) -> bool:
    if widget.property("mn_spellcheck_disabled") is True:
        return False
    if isinstance(widget, QLineEdit):
        if widget.isReadOnly():
            return False
        if widget.echoMode() != QLineEdit.EchoMode.Normal:
            return False
        if widget.maxLength() == 1:
            return False
    if isinstance(widget, (QPlainTextEdit, QTextEdit)) and widget.isReadOnly():
        return False
    name = (widget.objectName() or "").strip().lower()
    placeholder = ""
    if isinstance(widget, QLineEdit):
        placeholder = (widget.placeholderText() or "").strip().lower()
    elif isinstance(widget, (QPlainTextEdit, QTextEdit)):
        placeholder = (widget.placeholderText() or "").strip().lower()
    if any(hint in name for hint in _SKIP_NAME_HINTS):
        return False
    if any(hint in placeholder for hint in _SKIP_PLACEHOLDER_HINTS):
        return False
    return True


class _LineEditSpellOverlay(QWidget):
    def __init__(self, line_edit: QLineEdit) -> None:
        super().__init__(line_edit)
        self._line_edit = line_edit
        self._issues: list[SpellCheckIssue] = []
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setStyleSheet("background: transparent;")
        self.hide()

    def set_issues(self, issues: Sequence[SpellCheckIssue]) -> None:
        self._issues = list(issues)
        self.setVisible(bool(self._issues))
        self.update()

    def sync_geometry(self) -> None:
        self.setGeometry(self._line_edit.rect())
        self.raise_()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().paintEvent(event)
        if not self._issues:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(_SPELLCHECK_COLOR)
        cursor_rect = self._line_edit.cursorRect()
        text = self._line_edit.text()
        font_metrics = self._line_edit.fontMetrics()
        cursor_pos = self._line_edit.cursorPosition()
        cursor_prefix_width = font_metrics.horizontalAdvance(text[:cursor_pos])
        baseline = min(self.height() - 3, cursor_rect.bottom() + 1)
        clip_rect = self.rect().adjusted(2, 0, -2, 0)
        for issue in self._issues:
            start_width = font_metrics.horizontalAdvance(text[:issue.start])
            end_width = font_metrics.horizontalAdvance(text[: issue.start + issue.length])
            start_x = cursor_rect.x() - (cursor_prefix_width - start_width)
            end_x = cursor_rect.x() - (cursor_prefix_width - end_width)
            self._draw_wave(painter, QRect(start_x, baseline - 2, end_x - start_x, 4).intersected(clip_rect))

    @staticmethod
    def _draw_wave(painter: QPainter, rect: QRect) -> None:
        if rect.width() <= 2:
            return
        x = rect.left()
        upper_y = rect.top()
        lower_y = rect.bottom()
        while x < rect.right():
            painter.drawLine(x, lower_y, min(x + 2, rect.right()), upper_y)
            painter.drawLine(min(x + 2, rect.right()), upper_y, min(x + 4, rect.right()), lower_y)
            x += 4


class _BaseSpellController(QObject):
    def __init__(self, widget: QWidget, backend: _SpellCheckBackend, delay_ms: int) -> None:
        super().__init__(widget)
        self.widget = widget
        self._backend = backend
        self.issues: list[SpellCheckIssue] = []
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(max(0, delay_ms))
        self._timer.timeout.connect(self.refresh_now)

    def schedule_refresh(self) -> None:
        if not self._backend.enabled:
            return
        self._timer.start()

    def refresh_now(self) -> None:
        text = self.current_text()
        self.issues = self._backend.analyze_text(text)
        self.apply_issues(self.issues)

    def ignore_word(self, word: str) -> None:
        self._backend.ignore_word(word)
        self.refresh_now()

    def issue_at_position(self, position: int) -> SpellCheckIssue | None:
        for issue in self.issues:
            if issue.start <= position < issue.start + issue.length:
                return issue
        return None

    def current_text(self) -> str:
        raise NotImplementedError

    def apply_issues(self, issues: Sequence[SpellCheckIssue]) -> None:
        raise NotImplementedError

    def replace_issue(self, issue: SpellCheckIssue, replacement: str) -> None:
        raise NotImplementedError

    def position_from_point(self, point: QPoint) -> int | None:
        raise NotImplementedError


class _LineEditSpellController(_BaseSpellController):
    def __init__(self, widget: QLineEdit, backend: _SpellCheckBackend, delay_ms: int) -> None:
        super().__init__(widget, backend, delay_ms)
        self.widget = widget
        self._overlay = _LineEditSpellOverlay(widget)
        widget.textChanged.connect(self.schedule_refresh)
        widget.cursorPositionChanged.connect(self._overlay.update)
        widget.installEventFilter(self)
        self._overlay.sync_geometry()
        self.schedule_refresh()

    def eventFilter(self, obj, event) -> bool:
        if obj is self.widget and event.type() in {
            QEvent.Type.Resize,
            QEvent.Type.Move,
            QEvent.Type.Show,
            QEvent.Type.FontChange,
            QEvent.Type.StyleChange,
        }:
            self._overlay.sync_geometry()
            self._overlay.update()
        return super().eventFilter(obj, event)

    def current_text(self) -> str:
        return self.widget.text()

    def apply_issues(self, issues: Sequence[SpellCheckIssue]) -> None:
        self._overlay.set_issues(issues)

    def replace_issue(self, issue: SpellCheckIssue, replacement: str) -> None:
        text = self.widget.text()
        updated = text[: issue.start] + replacement + text[issue.start + issue.length :]
        self.widget.setText(updated)
        self.widget.setCursorPosition(issue.start + len(replacement))
        self.refresh_now()

    def position_from_point(self, point: QPoint) -> int | None:
        return self.widget.cursorPositionAt(point)


class _TextEditSpellController(_BaseSpellController):
    def __init__(self, widget: QPlainTextEdit | QTextEdit, backend: _SpellCheckBackend, delay_ms: int) -> None:
        super().__init__(widget, backend, delay_ms)
        self.widget = widget
        widget.textChanged.connect(self.schedule_refresh)
        self.schedule_refresh()

    def current_text(self) -> str:
        return self.widget.toPlainText()

    def apply_issues(self, issues: Sequence[SpellCheckIssue]) -> None:
        selections = []
        for issue in issues:
            cursor = self.widget.textCursor()
            cursor.setPosition(issue.start)
            cursor.setPosition(issue.start + issue.length, QTextCursor.MoveMode.KeepAnchor)
            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format.setUnderlineColor(_SPELLCHECK_COLOR)
            selection.format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
            selections.append(selection)
        self.widget.setExtraSelections(selections)

    def replace_issue(self, issue: SpellCheckIssue, replacement: str) -> None:
        cursor = self.widget.textCursor()
        cursor.setPosition(issue.start)
        cursor.setPosition(issue.start + issue.length, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(replacement)
        self.widget.setTextCursor(cursor)
        self.refresh_now()

    def position_from_point(self, point: QPoint) -> int | None:
        return self.widget.cursorForPosition(point).position()


class GlobalSpellCheckService(QObject):
    def __init__(
        self,
        app: QApplication,
        backend: _SpellCheckBackend | None = None,
        *,
        check_delay_ms: int = 260,
    ) -> None:
        super().__init__(app)
        self._app = app
        self._backend = backend or _build_spellcheck_backend()
        self._check_delay_ms = check_delay_ms
        self._controllers: dict[int, _BaseSpellController] = {}
        if self._backend.enabled:
            app.installEventFilter(self)

    @property
    def enabled(self) -> bool:
        return self._backend.enabled

    def attach_widget_tree(self, root: QWidget) -> None:
        if not self._backend.enabled:
            return
        self._maybe_attach(root)
        for widget in root.findChildren(QWidget):
            self._maybe_attach(widget)

    def eventFilter(self, obj, event) -> bool:
        if not self._backend.enabled:
            return super().eventFilter(obj, event)
        if isinstance(obj, QWidget) and event.type() == QEvent.Type.Show:
            self.attach_widget_tree(obj)
        if isinstance(obj, (QLineEdit, QPlainTextEdit, QTextEdit)) and event.type() == QEvent.Type.ContextMenu:
            context_event = cast(QContextMenuEvent, event)
            if self._show_context_menu(obj, context_event):
                return True
        return super().eventFilter(obj, event)

    def _maybe_attach(self, widget: QWidget) -> None:
        if id(widget) in self._controllers or not _should_attach_spellcheck(widget):
            return
        controller: _BaseSpellController | None = None
        if isinstance(widget, QLineEdit):
            controller = _LineEditSpellController(widget, self._backend, self._check_delay_ms)
        elif isinstance(widget, (QPlainTextEdit, QTextEdit)):
            controller = _TextEditSpellController(widget, self._backend, self._check_delay_ms)
        if controller is None:
            return
        key = id(widget)
        self._controllers[key] = controller
        widget.destroyed.connect(lambda *_args, widget_key=key: self._controllers.pop(widget_key, None))

    def _controller_for_widget(self, widget: QWidget) -> _BaseSpellController | None:
        return self._controllers.get(id(widget))

    def _insert_spelling_submenu(
        self,
        menu: QMenu,
        first_standard_action,
        controller: _BaseSpellController,
        issue: SpellCheckIssue,
    ):
        spelling_menu = QMenu("Проверка орфографии", menu)
        if issue.suggestions:
            for suggestion in issue.suggestions:
                action = spelling_menu.addAction(suggestion)
                action.triggered.connect(
                    lambda _checked=False, current_issue=issue, replacement=suggestion: controller.replace_issue(
                        current_issue, replacement
                    )
                )
        else:
            no_suggestions_action = spelling_menu.addAction("Нет вариантов")
            no_suggestions_action.setEnabled(False)
        spelling_menu.addSeparator()
        ignore_action = spelling_menu.addAction("Игнорировать слово")
        ignore_action.triggered.connect(
            lambda _checked=False, current_word=issue.word: controller.ignore_word(current_word)
        )
        return menu.insertMenu(first_standard_action, spelling_menu)

    def _show_context_menu(
        self,
        widget: QLineEdit | QPlainTextEdit | QTextEdit,
        event: QContextMenuEvent,
    ) -> bool:
        controller = self._controller_for_widget(widget)
        if controller is None:
            return False
        position = controller.position_from_point(event.pos())
        if position is None:
            return False
        issue = controller.issue_at_position(position)
        if isinstance(widget, QLineEdit):
            widget.setCursorPosition(position)
        else:
            widget.setTextCursor(widget.cursorForPosition(event.pos()))
        menu = widget.createStandardContextMenu()
        if not isinstance(menu, QMenu):
            return False
        try:
            if issue is not None:
                first_standard_action = menu.actions()[0] if menu.actions() else None
                self._insert_spelling_submenu(menu, first_standard_action, controller, issue)
                menu.insertSeparator(first_standard_action)
                menu.exec(event.globalPos())
                return True
            menu.exec(event.globalPos())
        finally:
            menu.deleteLater()
        return True


def install_global_spellcheck(app: QApplication) -> GlobalSpellCheckService:
    service = GlobalSpellCheckService(app)
    setattr(app, "_mn_spellcheck_service", service)
    return service


__all__ = [
    "GlobalSpellCheckService",
    "SpellCheckIssue",
    "install_global_spellcheck",
    "iter_spellcheck_tokens",
]
