from __future__ import annotations

from pathlib import Path

import pytest

from benchmarks.rag_comparison.adapters.deeptutor_parser import load_texts


def test_load_texts_uses_shared_parse_service(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "lesson.pdf"
    source.write_bytes(b"%PDF")
    calls: list[Path] = []

    class _Service:
        def parse(self, path: Path):
            calls.append(path)
            return type("Document", (), {"markdown": "# Parsed lesson"})()

    monkeypatch.setattr(
        "deeptutor.services.parsing.get_parse_service", lambda: _Service()
    )

    assert load_texts([str(source)]) == ["# Parsed lesson"]
    assert calls == [source]
