"""Test de humo: el pipeline completo, offline desde data/cache, reproduce
exactamente los exports commiteados."""
from pathlib import Path

import pytest

from authors.cli import CACHE_DIR, EXPORT_DIR, main

pytestmark = pytest.mark.skipif(not CACHE_DIR.exists(), reason="sin data/cache")


def test_offline_run_reproduces_committed_exports(tmp_path: Path):
    exit_code = main([
        "--offline",
        "--db", str(tmp_path / "authors.db"),
        "--export-dir", str(tmp_path / "export"),
        "--report", str(tmp_path / "QUALITY_REPORT.md"),
        "run",
    ])
    assert exit_code == 0
    for name in ("authors.csv", "seed_resolution.csv"):
        generated = (tmp_path / "export" / name).read_bytes()
        committed = (EXPORT_DIR / name).read_bytes()
        assert generated == committed, f"{name} difiere del export commiteado"
    assert (tmp_path / "QUALITY_REPORT.md").read_text(encoding="utf-8").startswith("# Informe de calidad")
