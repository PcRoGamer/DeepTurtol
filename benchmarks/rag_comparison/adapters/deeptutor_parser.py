"""Production-equivalent document loading for RAG benchmarks."""

from __future__ import annotations

from pathlib import Path


def load_texts(doc_paths: list[str]) -> list[str]:
    """Parse documents through DeepTutor's configured shared parse service.

    Benchmark adapters consume the resulting Markdown/text, rather than reading
    source files directly. This makes parser selection, parsing latency, and
    parse failures part of the measured ingestion path, just as they are when a
    DeepTutor knowledge base is created.
    """
    from deeptutor.services.parsing import ParserError, get_parse_service

    parse_service = get_parse_service()
    texts: list[str] = []
    failures: list[str] = []
    for raw_path in doc_paths:
        path = Path(raw_path)
        try:
            document = parse_service.parse(path)
        except ParserError as exc:
            failures.append(f"{path.name}: {exc}")
            continue
        text = document.markdown.strip()
        if text:
            texts.append(text)
        else:
            failures.append(f"{path.name}: parser returned no text")

    if failures:
        raise RuntimeError("DeepTutor parse failed: " + "; ".join(failures))
    return texts


__all__ = ["load_texts"]
