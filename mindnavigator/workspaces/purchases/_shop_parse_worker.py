"""_ShopParseWorker class module for purchases workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class _ShopParseWorker(QRunnable):
    def __init__(
        self,
        service: ShopParseService,
        sources: list,
        should_stop: Callable[[], bool],
    ) -> None:
        super().__init__()
        self._service = service
        self._sources = sources
        self._should_stop = should_stop
        self.signals = _ShopParseWorkerSignals()

    def run(self) -> None:
        total = len(self._sources)
        done = 0
        for source in self._sources:
            if self._should_stop():
                self.signals.message.emit("Обновление остановлено")
                break
            try:
                self._service.parse_and_store(source.url, item_id=source.item_id)
            except (ValueError, HttpClientError) as exc:
                self.signals.message.emit(str(exc))
            done += 1
            self.signals.progress.emit(done, total)
        self.signals.finished.emit()

__all__ = ["_ShopParseWorker"]
