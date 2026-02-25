"""CSV import/export helpers for workspace data transfer."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Iterable, Mapping, Sequence


class CsvTransferError(RuntimeError):
    """Raised when CSV input/output cannot be processed."""


@dataclass(frozen=True)
class CsvTransferOptions:
    """Options for CSV import/export behavior."""

    delimiter: str = ","
    quotechar: str = '"'
    encoding: str = "utf-8"


class CsvTransferService:
    """Converts row mappings between in-memory structures and CSV text/files."""

    def export_to_string(
        self,
        rows: Iterable[Mapping[str, object]],
        *,
        fieldnames: Sequence[str] | None = None,
        options: CsvTransferOptions | None = None,
    ) -> str:
        cfg = options or CsvTransferOptions()
        row_list = [dict(row) for row in rows]
        headers = self._resolve_fieldnames(row_list, fieldnames)

        buffer = StringIO(newline="")
        writer = csv.DictWriter(
            buffer,
            fieldnames=headers,
            delimiter=cfg.delimiter,
            quotechar=cfg.quotechar,
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in row_list:
            writer.writerow({key: self._normalize_cell(row.get(key)) for key in headers})
        return buffer.getvalue()

    def import_from_string(
        self,
        csv_text: str,
        *,
        options: CsvTransferOptions | None = None,
    ) -> list[dict[str, str]]:
        cfg = options or CsvTransferOptions()
        buffer = StringIO(csv_text or "", newline="")
        reader = csv.DictReader(
            buffer,
            delimiter=cfg.delimiter,
            quotechar=cfg.quotechar,
        )
        if not reader.fieldnames:
            raise CsvTransferError("CSV header row is required.")

        rows: list[dict[str, str]] = []
        for row in reader:
            rows.append({key: "" if value is None else str(value) for key, value in row.items()})
        return rows

    def export_to_file(
        self,
        path: Path | str,
        rows: Iterable[Mapping[str, object]],
        *,
        fieldnames: Sequence[str] | None = None,
        options: CsvTransferOptions | None = None,
    ) -> None:
        cfg = options or CsvTransferOptions()
        csv_text = self.export_to_string(rows, fieldnames=fieldnames, options=cfg)
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(csv_text, encoding=cfg.encoding, newline="")

    def import_from_file(
        self,
        path: Path | str,
        *,
        options: CsvTransferOptions | None = None,
    ) -> list[dict[str, str]]:
        cfg = options or CsvTransferOptions()
        source_path = Path(path)
        try:
            csv_text = source_path.read_text(encoding=cfg.encoding)
        except OSError as exc:
            raise CsvTransferError(str(exc)) from exc
        return self.import_from_string(csv_text, options=cfg)

    @staticmethod
    def _resolve_fieldnames(
        rows: list[dict[str, object]],
        fieldnames: Sequence[str] | None,
    ) -> list[str]:
        if fieldnames is not None:
            headers = [str(name) for name in fieldnames if str(name)]
            if headers:
                return headers
            raise CsvTransferError("CSV fieldnames cannot be empty.")

        ordered_headers: list[str] = []
        seen_headers: set[str] = set()
        for row in rows:
            for key in row:
                key_name = str(key)
                if key_name and key_name not in seen_headers:
                    seen_headers.add(key_name)
                    ordered_headers.append(key_name)
        if not ordered_headers:
            raise CsvTransferError("Cannot export CSV without at least one column.")
        return ordered_headers

    @staticmethod
    def _normalize_cell(value: object) -> str:
        if value is None:
            return ""
        return str(value)
