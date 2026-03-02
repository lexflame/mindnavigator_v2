from __future__ import annotations

import os
import shutil
from pathlib import Path
from uuid import uuid4

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture()
def unique_temp_path():
    # Keep test temp files out of pytest's own tempdir cleanup path due local ACL instability.
    base_dir = Path.cwd() / ".test_runtime" / uuid4().hex
    base_dir.mkdir(parents=True, exist_ok=True)

    def _build(prefix: str, suffix: str) -> Path:
        return base_dir / f"{prefix}_{uuid4().hex}{suffix}"

    try:
        yield _build
    finally:
        shutil.rmtree(base_dir, ignore_errors=True)
