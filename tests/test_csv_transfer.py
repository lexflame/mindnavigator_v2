from __future__ import annotations

import pytest

from mindnavigator.transfer.collections import CsvTransferError, CsvTransferOptions, CsvTransferService

def test_csv_round_trip_with_multiline_and_special_symbols() -> None:
    service = CsvTransferService()
    rows = [
        {
            "title": "Alpha, Beta",
            "description": "line1\nline2",
            "note": "quote \"inside\"",
        },
        {
            "title": "Unicode",
            "description": "Пример",
            "note": "中文",
        },
    ]

    csv_text = service.export_to_string(rows)
    parsed = service.import_from_string(csv_text)

    assert parsed == [
        {
            "title": "Alpha, Beta",
            "description": "line1\nline2",
            "note": 'quote "inside"',
        },
        {
            "title": "Unicode",
            "description": "Пример",
            "note": "中文",
        },
    ]


def test_csv_supports_custom_delimiter() -> None:
    service = CsvTransferService()
    options = CsvTransferOptions(delimiter=";")
    rows = [{"a": "1", "b": "2;3"}]

    csv_text = service.export_to_string(rows, options=options)
    parsed = service.import_from_string(csv_text, options=options)

    assert parsed == [{"a": "1", "b": "2;3"}]


def test_csv_file_round_trip(unique_temp_path) -> None:
    service = CsvTransferService()
    path = unique_temp_path("csv_transfer", ".csv")

    rows = [{"id": 1, "name": "Task"}, {"id": 2, "name": "Task 2"}]
    service.export_to_file(path, rows)
    parsed = service.import_from_file(path)

    assert parsed == [{"id": "1", "name": "Task"}, {"id": "2", "name": "Task 2"}]


def test_csv_import_requires_header_row() -> None:
    service = CsvTransferService()

    with pytest.raises(CsvTransferError):
        service.import_from_string("", options=CsvTransferOptions())
