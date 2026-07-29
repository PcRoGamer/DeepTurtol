"""Quick verification that everything works together."""
import json
import sys
from pathlib import Path

CORPUS_DIR = Path(__file__).parent.parent / "corpus"
ADAPTERS_DIR = Path(__file__).parent.parent / "adapters"

def test_corpus():
    manifest = json.loads((CORPUS_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert (CORPUS_DIR / "manifest.json").exists(), "manifest.json missing"
    assert len(manifest["documents"]) == 20, f"Expected 20 docs, got {len(manifest['documents'])}"
    counts = {}
    for doc in manifest["documents"]:
        counts[doc["stage"]] = counts.get(doc["stage"], 0) + 1
    assert counts["stage1"] == 5, f"stage1: expected 5, got {counts.get('stage1')}"
    assert counts["stage2"] == 5, f"stage2: expected 5, got {counts.get('stage2')}"
    assert counts["stage3"] == 10, f"stage3: expected 10, got {counts.get('stage3')}"
    assert len(manifest["qa_pairs"]) == 30, f"Expected 30 QA, got {len(manifest['qa_pairs'])}"
    types = {q["type"] for q in manifest["qa_pairs"]}
    assert types == {"factual_recall", "multi_hop", "synthesis"}
    for doc in manifest["documents"]:
        filepath = CORPUS_DIR / doc["path"]
        assert filepath.exists(), f"Missing: {doc['path']}"
        content = filepath.read_text(encoding="utf-8")
        assert len(content) > 100, f"Too short: {doc['path']}"
    print("PASS: corpus (20 docs, 30 QA, all files present)")

def test_adapters():
    assert (ADAPTERS_DIR / "base.py").exists(), "base.py missing"
    assert (ADAPTERS_DIR / "lightrag_adapter.py").exists(), "lightrag_adapter.py missing"
    assert (ADAPTERS_DIR / "leanrag_adapter.py").exists(), "leanrag_adapter.py missing"
    assert (ADAPTERS_DIR / "__init__.py").exists(), "__init__.py missing"
    print("PASS: adapters (base + lightrag + leanrag)")

def test_benchmark():
    bench = Path(__file__).parent.parent / "benchmark.py"
    assert bench.exists(), "benchmark.py missing"
    content = bench.read_text(encoding="utf-8")
    assert "async def" in content, "benchmark.py missing async functions"
    assert "argparse" in content, "benchmark.py missing argparse"
    assert "Rich" in content or "rich" in content, "benchmark.py missing rich output"
    print("PASS: benchmark runner")

def test_evaluate():
    ev = Path(__file__).parent.parent / "evaluate.py"
    assert ev.exists(), "evaluate.py missing"
    content = ev.read_text(encoding="utf-8")
    assert "ragas" in content.lower(), "evaluate.py missing ragas"
    assert "argparse" in content, "evaluate.py missing argparse"
    print("PASS: RAGAS evaluator")

def test_config():
    config_path = Path(__file__).parent.parent / "config.yaml"
    assert config_path.exists(), "config.yaml missing"
    import yaml
    config = yaml.safe_load(config_path.read_text())
    assert "llm" in config, "config missing llm section"
    assert "embedding" in config, "config missing embedding section"
    assert "leanrag" in config, "config missing leanrag section"
    print("PASS: config.yaml")

def test_docker():
    docker_path = Path(__file__).parent.parent / "docker" / "docker-compose.yml"
    assert docker_path.exists(), "docker-compose.yml missing"
    print("PASS: docker-compose.yml")

if __name__ == "__main__":
    tests = [test_corpus, test_adapters, test_benchmark, test_evaluate, test_config, test_docker]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1
    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed, {passed+failed} total")
    sys.exit(1 if failed else 0)
