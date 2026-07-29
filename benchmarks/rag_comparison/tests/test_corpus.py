import json
from pathlib import Path

CORPUS_DIR = Path(__file__).parent.parent / "corpus"

def test_manifest_exists():
    assert (CORPUS_DIR / "manifest.json").exists()

def test_all_stage_files_exist():
    manifest = json.loads((CORPUS_DIR / "manifest.json").read_text())
    for doc in manifest["documents"]:
        filepath = CORPUS_DIR / doc["path"]
        assert filepath.exists(), f"Missing: {doc['path']}"

def test_document_count():
    manifest = json.loads((CORPUS_DIR / "manifest.json").read_text())
    assert len(manifest["documents"]) == 20

def test_stage_counts():
    manifest = json.loads((CORPUS_DIR / "manifest.json").read_text())
    counts = {}
    for doc in manifest["documents"]:
        counts[doc["stage"]] = counts.get(doc["stage"], 0) + 1
    assert counts.get("stage1") == 5
    assert counts.get("stage2") == 5
    assert counts.get("stage3") == 10

def test_qa_pair_count():
    manifest = json.loads((CORPUS_DIR / "manifest.json").read_text())
    assert len(manifest["qa_pairs"]) == 30

def test_qa_types():
    manifest = json.loads((CORPUS_DIR / "manifest.json").read_text())
    types = {q["type"] for q in manifest["qa_pairs"]}
    assert types == {"factual_recall", "multi_hop", "synthesis"}

def test_documents_are_nonempty():
    manifest = json.loads((CORPUS_DIR / "manifest.json").read_text())
    for doc in manifest["documents"]:
        content = (CORPUS_DIR / doc["path"]).read_text(encoding="utf-8")
        assert len(content) > 100, f"Document too short: {doc['path']}"
