"""RAG benchmark orchestrator.

Runs the configured engines through four incremental-indexing stages using
DeepTutor's shared document-parse path, collects end-to-end performance
metrics, and writes a raw JSON dump plus a Markdown report to ``results/``.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = BASE_DIR / "config.yaml"
MANIFEST_PATH = BASE_DIR / "corpus" / "manifest.json"
RESULTS_DIR = BASE_DIR / "results"

STAGES = ["stage1", "stage2", "stage3"]

logger = logging.getLogger(__name__)
console = Console()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_config(path: Path) -> dict:
    """Load and return the YAML config file."""
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_manifest(path: Path) -> dict:
    """Load and return the corpus manifest."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def get_stage_files(stage: str, manifest: dict) -> list[str]:
    """Return absolute paths for all .md files belonging to *stage*."""
    corpus_dir = BASE_DIR / "corpus"
    return [
        str(corpus_dir / doc["path"])
        for doc in manifest["documents"]
        if doc["stage"] == stage
    ]


def get_all_files_up_to(last_stage: str, manifest: dict) -> list[str]:
    """Return absolute paths for all files up to and including *last_stage*."""
    corpus_dir = BASE_DIR / "corpus"
    stage_order = STAGES
    cutoff = stage_order.index(last_stage) + 1
    return [
        str(corpus_dir / doc["path"])
        for doc in manifest["documents"]
        if doc["stage"] in stage_order[:cutoff]
    ]


def get_stage_qa_pairs(last_stage: str, manifest: dict) -> list[dict]:
    """Keep only questions answerable from documents indexed at this stage."""
    cutoff = STAGES.index(last_stage) + 1
    available = {
        doc["filename"]
        for doc in manifest["documents"]
        if doc["stage"] in STAGES[:cutoff]
    }
    return [
        qa for qa in manifest["qa_pairs"]
        if set(qa.get("source_docs", [])).issubset(available)
    ]


def compute_percentiles(query_times: list[float]) -> dict[str, float]:
    """Compute p50, p95, p99 percentiles from a list of durations (seconds).

    Uses the simple nearest-rank method: sort the list and pick the value
    at the ceiling index for each percentile.
    """
    if not query_times:
        return {"p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0}
    sorted_times = sorted(query_times)
    n = len(sorted_times)

    def _percentile(p: float) -> float:
        rank = max(0, min(n - 1, int(p / 100.0 * n)))
        return sorted_times[rank] * 1000.0  # convert to ms

    return {
        "p50_ms": round(_percentile(50), 2),
        "p95_ms": round(_percentile(95), 2),
        "p99_ms": round(_percentile(99), 2),
    }


async def run_queries(
    adapter: Any,
    qa_pairs: list[dict],
    console: Console,
    label: str = "",
) -> dict[str, Any]:
    """Run all QA pairs against *adapter* and return metrics.

    Returns a dict with ``query_times_s``, ``answers``, and percentile
    statistics.
    """
    query_times: list[float] = []
    answers: list[str] = []

    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold cyan]{label} querying…"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("query", total=len(qa_pairs))
        for qa in qa_pairs:
            answer, elapsed = await adapter.query_timed(qa["question"])
            query_times.append(elapsed)
            answers.append(answer)
            progress.advance(task)

    percentiles = compute_percentiles(query_times)
    return {
        "query_times_s": query_times,
        "answers": answers,
        **percentiles,
    }


async def run_adapter_stages(
    adapter: Any,
    adapter_name: str,
    manifest: dict,
    skip_rebuild: bool,
) -> dict[str, Any]:
    """Run the full 4-stage benchmark for one adapter.

    Returns a dict keyed by stage name with per-stage metrics.
    """
    results: dict[str, Any] = {}

    # --- Stage 1: Fresh index from stage1 files -------------------------
    console.rule(f"[bold green]{adapter_name} — Stage 1: Initial index")
    stage1_files = get_stage_files("stage1", manifest)
    console.print(f"  Indexing {len(stage1_files)} files…")

    index_time = await adapter.index(stage1_files, label="stage1")
    index_size = adapter.get_index_size()
    stage1_qa = get_stage_qa_pairs("stage1", manifest)
    query_results = await run_queries(adapter, stage1_qa, console, label=f"{adapter_name}/s1")

    results["stage1"] = {
        "index_time_s": round(index_time, 3),
        "index_size_bytes": index_size,
        "qa_ids": [qa["id"] for qa in stage1_qa],
        **query_results,
    }
    console.print(
        f"  [green]✓[/] Indexed in {index_time:.2f}s | "
        f"Index size: {index_size:,} bytes | "
        f"Query p50={query_results['p50_ms']:.0f}ms "
        f"p95={query_results['p95_ms']:.0f}ms "
        f"p99={query_results['p99_ms']:.0f}ms"
    )

    # --- Stage 2: Add stage2 documents ----------------------------------
    console.rule(f"[bold green]{adapter_name} — Stage 2: Incremental add")
    stage2_files = get_stage_files("stage2", manifest)
    console.print(f"  Adding {len(stage2_files)} files…")

    add_time = await adapter.add_documents(stage2_files, label="stage2")
    index_size = adapter.get_index_size()
    stage2_qa = get_stage_qa_pairs("stage2", manifest)
    query_results = await run_queries(adapter, stage2_qa, console, label=f"{adapter_name}/s2")

    results["stage2"] = {
        "add_time_s": round(add_time, 3),
        "index_size_bytes": index_size,
        "qa_ids": [qa["id"] for qa in stage2_qa],
        **query_results,
    }
    console.print(
        f"  [green]✓[/] Added in {add_time:.2f}s | "
        f"Index size: {index_size:,} bytes | "
        f"Query p50={query_results['p50_ms']:.0f}ms "
        f"p95={query_results['p95_ms']:.0f}ms "
        f"p99={query_results['p99_ms']:.0f}ms"
    )

    # --- Stage 3: Add stage3 documents ----------------------------------
    console.rule(f"[bold green]{adapter_name} — Stage 3: Incremental add")
    stage3_files = get_stage_files("stage3", manifest)
    console.print(f"  Adding {len(stage3_files)} files…")

    add_time = await adapter.add_documents(stage3_files, label="stage3")
    index_size = adapter.get_index_size()
    stage3_qa = get_stage_qa_pairs("stage3", manifest)
    query_results = await run_queries(adapter, stage3_qa, console, label=f"{adapter_name}/s3")

    results["stage3"] = {
        "add_time_s": round(add_time, 3),
        "index_size_bytes": index_size,
        "qa_ids": [qa["id"] for qa in stage3_qa],
        **query_results,
    }
    console.print(
        f"  [green]✓[/] Added in {add_time:.2f}s | "
        f"Index size: {index_size:,} bytes | "
        f"Query p50={query_results['p50_ms']:.0f}ms "
        f"p95={query_results['p95_ms']:.0f}ms "
        f"p99={query_results['p99_ms']:.0f}ms"
    )

    # --- Stage 4 (supplementary): Full rebuild --------------------------
    if not skip_rebuild:
        console.rule(f"[bold yellow]{adapter_name} — Stage 4: Full rebuild (supplementary)")
        all_files = get_all_files_up_to("stage3", manifest)
        console.print(f"  Rebuilding index from {len(all_files)} files…")

        await adapter.delete()
        # Deletion finalizes storage handles. Recreate them before inserting the
        # rebuild corpus (especially required by LightRAG's JSON stores).
        await adapter.initialize()
        rebuild_time = await adapter.index(all_files, label="stage4-rebuild")
        index_size = adapter.get_index_size()
        stage4_qa = get_stage_qa_pairs("stage3", manifest)
        query_results = await run_queries(adapter, stage4_qa, console, label=f"{adapter_name}/s4")

        results["stage4_rebuild"] = {
            "index_time_s": round(rebuild_time, 3),
            "index_size_bytes": index_size,
            "qa_ids": [qa["id"] for qa in stage4_qa],
            **query_results,
        }
        console.print(
            f"  [green]✓[/] Rebuilt in {rebuild_time:.2f}s | "
            f"Index size: {index_size:,} bytes | "
            f"Query p50={query_results['p50_ms']:.0f}ms "
            f"p95={query_results['p95_ms']:.0f}ms "
            f"p99={query_results['p99_ms']:.0f}ms"
        )

    return results


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(
    raw: dict[str, Any],
    adapters_run: list[str],
    skip_rebuild: bool,
) -> str:
    """Generate a Markdown report from raw results."""
    lines: list[str] = []
    ts = raw["timestamp"]
    lines.append(f"# RAG Benchmark Report — {ts}\n")
    lines.append(
        f"**LLM:** {raw['config']['llm_model']}  |  "
        f"**Embedding:** {raw['config']['embedding_model']}\n"
    )
    lines.append("")

    # --- Speed summary table -------------------------------------------
    lines.append("## Speed\n")
    lines.append("| Metric |", )
    for name in adapters_run:
        lines[0] += f" {name} |"
    lines.append("")
    lines.append("| --- |" + " --- |" * len(adapters_run))

    for stage in STAGES:
        build_key = "index_time_s" if stage == "stage1" else "add_time_s"
        build_label = "Index time" if stage == "stage1" else f"Add time ({stage})"
        row = f"| **{build_label}** |"
        for name in adapters_run:
            stage_data = raw.get(name, {}).get(stage, {})
            val = stage_data.get(build_key, "—")
            row += f" {val:.2f}s |" if isinstance(val, (int, float)) else f" {val} |"
        lines.append(row)

        for pct_label, pct_key in [("p50", "p50_ms"), ("p95", "p95_ms"), ("p99", "p99_ms")]:
            row = f"| Query {pct_label} |"
            for name in adapters_run:
                stage_data = raw.get(name, {}).get(stage, {})
                val = stage_data.get(pct_key, "—")
                row += f" {val:.0f}ms |" if isinstance(val, (int, float)) else f" {val} |"
            lines.append(row)

    lines.append("")

    # --- Growth overhead ------------------------------------------------
    lines.append("## Growth Overhead\n")
    lines.append("Time cost for each incremental document addition.\n")
    lines.append("| Increment |", )
    for name in adapters_run:
        lines[len(lines) - 1] += f" {name} |"
    lines[-1] += ""
    lines.append("| --- |" + " --- |" * len(adapters_run))

    increments = [
        ("stage2 — add 5 docs", "stage2", "add_time_s"),
        ("stage3 — add 10 docs", "stage3", "add_time_s"),
    ]
    for label, stage, key in increments:
        row = f"| {label} |"
        for name in adapters_run:
            val = raw.get(name, {}).get(stage, {}).get(key, "—")
            row += f" {val:.2f}s |" if isinstance(val, (int, float)) else f" {val} |"
        lines.append(row)
    lines.append("")

    # --- Stage 4 rebuild (supplementary) --------------------------------
    if not skip_rebuild and any(
        "stage4_rebuild" in raw.get(name, {}) for name in adapters_run
    ):
        lines.append("## Stage 4 — Full Rebuild (supplementary)\n")
        lines.append(
            "Delete everything, then rebuild the full 20-document index.\n"
        )
        lines.append("| Metric |", )
        for name in adapters_run:
            lines[len(lines) - 1] += f" {name} |"
        lines[-1] += ""
        lines.append("| --- |" + " --- |" * len(adapters_run))

        rebuild_data = {n: raw.get(n, {}).get("stage4_rebuild", {}) for n in adapters_run}

        row = "| Index time |"
        for name in adapters_run:
            val = rebuild_data[name].get("index_time_s", "—")
            row += f" {val:.2f}s |" if isinstance(val, (int, float)) else f" {val} |"
        lines.append(row)

        row = "| Index size |"
        for name in adapters_run:
            val = rebuild_data[name].get("index_size_bytes", "—")
            row += f" {val:,} bytes |" if isinstance(val, (int, float)) else f" {val} |"
        lines.append(row)

        for pct_label, pct_key in [("p50", "p50_ms"), ("p95", "p95_ms"), ("p99", "p99_ms")]:
            row = f"| Query {pct_label} |"
            for name in adapters_run:
                val = rebuild_data[name].get(pct_key, "—")
                row += f" {val:.0f}ms |" if isinstance(val, (int, float)) else f" {val} |"
            lines.append(row)

        lines.append("")

    lines.append("---\n")
    lines.append("*RAGAS evaluation scores are not included here — see `evaluate.py`.*\n")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Adapter factory
# ---------------------------------------------------------------------------

def build_adapter(name: str, config: dict) -> Any:
    """Instantiate an adapter by name from config."""
    llm = config["llm"]
    emb = config["embedding"]

    if name == "kag":
        from adapters.kag_adapter import KAGAdapter
        return KAGAdapter()

    if name == "lightrag":
        from adapters.lightrag_adapter import LightRAGAdapter

        return LightRAGAdapter(
            working_dir=str(BASE_DIR / "vendor" / f"lightrag_benchmark"),
            llm_base_url=llm["base_url"],
            llm_api_key=llm["api_key"],
            llm_model=llm["model"],
            embedding_model=emb.get("model", "Qwen/Qwen3-Embedding-0.6B"),
            embedding_dim=emb.get("dimension", 1024),
        )

    if name == "leanrag":
        from adapters.leanrag_adapter import LeanRAGAdapter

        leanrag_cfg = config.get("leanrag", {}).get("mysql", {})
        return LeanRAGAdapter(
            working_dir=str(BASE_DIR / "vendor" / f"leanrag_benchmark"),
            llm_base_url=llm["base_url"],
            llm_api_key=llm["api_key"],
            llm_model=llm["model"],
            embedding_model=emb["model"],
            embedding_dim=emb["dimension"],
            mysql_host=leanrag_cfg.get("host", "localhost"),
            mysql_port=leanrag_cfg.get("port", 3306),
            mysql_user=leanrag_cfg.get("user", "root"),
            mysql_password=leanrag_cfg.get("password", ""),
        )

    raise ValueError(f"Unknown adapter: {name!r}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="RAG Benchmark — compare retrieval engines through DeepTutor parsing",
    )
    parser.add_argument(
        "--adapter",
        choices=["kag", "lightrag", "leanrag", "both"],
        default="both",
        help="Which adapter(s) to benchmark (default: both)",
    )
    parser.add_argument(
        "--skip-rebuild",
        action="store_true",
        help="Skip stage 4 (full rebuild / supplementary)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Path to config.yaml (default: config.yaml next to this script)",
    )
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    config = load_config(args.config)
    manifest = load_manifest(MANIFEST_PATH)

    # Determine which adapters to run
    if args.adapter == "both":
        adapter_names = ["kag", "lightrag"]
    else:
        adapter_names = [args.adapter]

    console.print(
        Panel(
            f"[bold]RAG Benchmark[/]\n"
            f"Adapters: {', '.join(adapter_names)}\n"
            f"Stages: 1->2->3{'->4 (rebuild)' if not args.skip_rebuild else ''}\n"
            f"QA pairs: {len(manifest['qa_pairs'])}",
            title="benchmark.py",
            border_style="blue",
        )
    )

    all_results: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {
            "llm_model": config["llm"]["model"],
            "embedding_model": config["embedding"]["model"],
        },
    }

    adapters_run: list[str] = []

    for name in adapter_names:
        console.rule(f"[bold magenta]Initializing {name}")
        try:
            adapter = build_adapter(name, config)
            work_dir = str(BASE_DIR / "vendor" / f"{name}_benchmark")
            await adapter.initialize(work_dir)
        except Exception:
            logger.exception("Failed to initialize %s — skipping", name)
            console.print(f"[bold red]✗[/] {name} initialization failed, skipping")
            continue

        try:
            stage_results = await run_adapter_stages(
                adapter,
                name,
                manifest,
                skip_rebuild=args.skip_rebuild,
            )
            all_results[name] = stage_results
            adapters_run.append(name)
        except Exception:
            logger.exception("Benchmark failed for %s", name)
            console.print(f"[bold red]✗[/] {name} benchmark failed, continuing")
        finally:
            try:
                await adapter.delete()
            except Exception:
                logger.debug("Cleanup failed for %s (non-fatal)", name)

    # --- Write outputs --------------------------------------------------
    if not adapters_run:
        console.print("[bold red]No adapters completed successfully.[/]")
        sys.exit(1)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts_label = datetime.now().strftime("%Y%m%d_%H%M%S")

    raw_path = RESULTS_DIR / f"{ts_label}_raw.json"
    with open(raw_path, "w", encoding="utf-8") as fh:
        json.dump(all_results, fh, indent=2, ensure_ascii=False)
    console.print(f"\n[bold green]✓[/] Raw results → {raw_path}")

    report_md = generate_report(all_results, adapters_run, args.skip_rebuild)
    report_path = RESULTS_DIR / f"{ts_label}_report.md"
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(report_md)
    console.print(f"[bold green]✓[/] Report → {report_path}")


def main() -> None:
    """Entry point (sync wrapper around async_main)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
