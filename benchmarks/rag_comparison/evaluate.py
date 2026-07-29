"""RAGAS evaluation script for the RAG comparison benchmark.

Reads a raw results JSON produced by the benchmark runner, runs RAGAS
evaluation (faithfulness, answer_relevancy, context_precision, context_recall),
writes scores back into the raw JSON, and appends a RAGAS scores table to the
corresponding markdown report.

Usage
-----
    python evaluate.py results/2026-07-27T..._raw.json
    python evaluate.py results/2026-07-27T..._raw.json --metric faithfulness,answer_relevancy
"""
from __future__ import annotations

import argparse
import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SYSTEMS = ("lightrag", "leanrag")
STAGES = ("stage1", "stage2", "stage3", "stage4_rebuild")

ALL_METRICS = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")

QUESTION_TYPES = ("factual_recall", "multi_hop", "synthesis")

CORPUS_DIR = Path(__file__).resolve().parent / "corpus"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_manifest() -> dict[str, Any]:
    """Load the corpus manifest and return it."""
    if not MANIFEST_PATH.exists():
        log.warning("Manifest not found at %s — per-type breakdowns will be empty", MANIFEST_PATH)
        return {"qa_pairs": []}
    with open(MANIFEST_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _qa_index(manifest: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Return ``{qa_id: {question, answer, type, ...}}``."""
    idx: dict[str, dict[str, str]] = {}
    for qa in manifest.get("qa_pairs", []):
        qa_id = qa["id"]
        # Some QA pairs may use ``output`` instead of ``answer`` (typo in data).
        answer = qa.get("answer") or qa.get("output") or ""
        idx[qa_id] = {
            "question": qa.get("question", ""),
            "answer": answer,
            "type": qa.get("type", "unknown"),
            "difficulty": qa.get("difficulty", "unknown"),
        }
    return idx


def _find_report_for_timestamp(timestamp: str, results_dir: Path) -> Path | None:
    """Locate the ``_report.md`` file whose name starts with the same date prefix."""
    # timestamp looks like 2026-07-27T123456 or 2026-07-27T12:34:56
    # The file on disk will use a filesystem-safe variant, e.g.
    #   2026-07-27T123456_report.md  or  2026-07-27T12_34_56_report.md
    date_prefix = timestamp.split("T")[0]
    for candidate in sorted(results_dir.glob("*_report.md"), reverse=True):
        if candidate.name.startswith(date_prefix):
            return candidate
    return None


# ---------------------------------------------------------------------------
# RAGAS evaluation
# ---------------------------------------------------------------------------


def _build_ragas_dataset(
    questions: list[str],
    answers: list[str],
    ground_truths: list[str],
) -> Any:
    """Create a HuggingFace ``Dataset`` suitable for RAGAS evaluation."""
    from datasets import Dataset

    # RAGAS expects ``contexts`` to be a list-of-lists.  Because we do not
    # have separate retrieval-context outputs from the benchmarked systems,
    # we use the generated answer as a single-element context list.
    contexts = [[a] for a in answers]

    return Dataset.from_dict(
        {
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths,
        }
    )


def _run_ragas(
    dataset: Any,
    metric_names: list[str],
) -> dict[str, float]:
    """Run RAGAS evaluation and return ``{metric_name: score}``."""
    from ragas import evaluate as ragas_evaluate
    import ragas.metrics as ragas_metrics

    metric_map = {
        "faithfulness": ragas_metrics.faithfulness,
        "answer_relevancy": ragas_metrics.answer_relevancy,
        "context_precision": ragas_metrics.context_precision,
        "context_recall": ragas_metrics.context_recall,
    }
    metrics = [metric_map[m] for m in metric_names if m in metric_map]
    if not metrics:
        log.warning("No valid metrics selected — skipping RAGAS evaluation")
        return {}

    result = ragas_evaluate(dataset, metrics=metrics)
    return {name: float(result[name]) for name in metric_names if name in result}


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def _format_scores_table(
    scores: dict[str, dict[str, dict[str, float]]],
    metric_names: list[str],
) -> str:
    """Render the full per-stage RAGAS scores as a markdown table block."""
    lines: list[str] = []
    lines.append("")
    lines.append("## RAGAS Evaluation Scores")
    lines.append("")
    lines.append(f"*Evaluated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    lines.append("")

    # Table header
    header = "| System | Stage | " + " | ".join(metric_names) + " |"
    sep = "|--------|-------|" + "|".join(["------" for _ in metric_names]) + "|"
    lines.append(header)
    lines.append(sep)

    for system in SYSTEMS:
        if system not in scores:
            continue
        for stage in STAGES:
            if stage not in scores[system]:
                continue
            row_scores = scores[system][stage]
            cells = [f"{row_scores.get(m, float('nan')):.4f}" for m in metric_names]
            lines.append(f"| {system} | {stage} | " + " | ".join(cells) + " |")

    lines.append("")
    return "\n".join(lines)


def _format_per_type_table(
    per_type_scores: dict[str, dict[str, dict[str, float]]],
    metric_names: list[str],
) -> str:
    """Render per-question-type RAGAS scores as a markdown table block."""
    if not per_type_scores:
        return ""

    lines: list[str] = []
    lines.append("")
    lines.append("## RAGAS Scores by Question Type")
    lines.append("")

    header = "| System | Question Type | " + " | ".join(metric_names) + " |"
    sep = "|--------|---------------|" + "|".join(["------" for _ in metric_names]) + "|"
    lines.append(header)
    lines.append(sep)

    for system in SYSTEMS:
        if system not in per_type_scores:
            continue
        for qtype in QUESTION_TYPES:
            if qtype not in per_type_scores[system]:
                continue
            row_scores = per_type_scores[system][qtype]
            cells = [f"{row_scores.get(m, float('nan')):.4f}" for m in metric_names]
            lines.append(f"| {system} | {qtype} | " + " | ".join(cells) + " |")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main evaluation logic
# ---------------------------------------------------------------------------


def evaluate_stage(
    system: str,
    stage: str,
    answers_raw: list[str],
    qa_index: dict[str, dict[str, str]],
    stage_qa_ids: list[str],
    metric_names: list[str],
) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    """Evaluate a single system + stage combination.

    Returns
    -------
    scores : dict[str, float]
        Overall RAGAS scores for this stage.
    per_type : dict[str, dict[str, float]]
        Scores broken down by question type.
    """
    questions: list[str] = []
    generated_answers: list[str] = []
    ground_truths: list[str] = []
    types: list[str] = []

    for i, qa_id in enumerate(stage_qa_ids):
        qa = qa_index.get(qa_id)
        if qa is None:
            log.debug("QA pair %s not found in manifest — skipping", qa_id)
            continue
        if i >= len(answers_raw):
            log.debug("No answer for QA %s in %s/%s — skipping", qa_id, system, stage)
            continue
        gen_answer = answers_raw[i]
        if not gen_answer or gen_answer.strip() == "":
            log.debug("Empty answer for QA %s in %s/%s — skipping", qa_id, system, stage)
            continue

        questions.append(qa["question"])
        generated_answers.append(gen_answer)
        ground_truths.append(qa["answer"])
        types.append(qa["type"])

    if not questions:
        log.warning("No valid QA pairs for %s/%s — skipping", system, stage)
        return {}, {}

    log.info(
        "Evaluating %s/%s with %d QA pairs …",
        system,
        stage,
        len(questions),
    )

    try:
        dataset = _build_ragas_dataset(questions, generated_answers, ground_truths)
        scores = _run_ragas(dataset, metric_names)
    except Exception:
        log.exception("RAGAS evaluation failed for %s/%s", system, stage)
        return {}, {}

    # Per-type breakdown
    per_type: dict[str, dict[str, float]] = defaultdict(dict)
    for qtype in QUESTION_TYPES:
        idxs = [j for j, t in enumerate(types) if t == qtype]
        if len(idxs) < 1:
            continue
        sub_qs = [questions[j] for j in idxs]
        sub_ans = [generated_answers[j] for j in idxs]
        sub_gt = [ground_truths[j] for j in idxs]
        try:
            sub_ds = _build_ragas_dataset(sub_qs, sub_ans, sub_gt)
            sub_scores = _run_ragas(sub_ds, metric_names)
            per_type[qtype] = sub_scores
        except Exception:
            log.exception(
                "RAGAS per-type evaluation failed for %s/%s/%s",
                system,
                stage,
                qtype,
            )

    return scores, dict(per_type)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run RAGAS evaluation on benchmark raw results.",
    )
    parser.add_argument(
        "results_json_path",
        type=Path,
        help="Path to the *_raw.json results file.",
    )
    parser.add_argument(
        "--metric",
        type=str,
        default=",".join(ALL_METRICS),
        help=(
            "Comma-separated list of RAGAS metrics to compute. "
            f"Default: {','.join(ALL_METRICS)}"
        ),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=MANIFEST_PATH,
        help="Path to corpus manifest.json (default: auto-detected).",
    )
    args = parser.parse_args(argv)

    results_path: Path = args.results_json_path.resolve()
    if not results_path.exists():
        log.error("Results file not found: %s", results_path)
        return 1

    metric_names = [m.strip() for m in args.metric.split(",") if m.strip()]
    if not metric_names:
        log.error("No metrics specified")
        return 1

    # Load inputs
    with open(results_path, encoding="utf-8") as fh:
        raw_results: dict[str, Any] = json.load(fh)

    manifest = _load_manifest()
    qa_index = _qa_index(manifest)

    # Build a mapping of question id → QA pair from the manifest (preserving
    # order) so we can correlate answers in the raw results with ground truths.
    qa_pairs = manifest.get("qa_pairs", [])
    qa_ids = [qa["id"] for qa in qa_pairs]

    timestamp = raw_results.get("timestamp", "")
    results_dir = results_path.parent

    # --- Run evaluation ---------------------------------------------------

    ragas_scores: dict[str, dict[str, dict[str, float]]] = {}
    all_per_type: dict[str, dict[str, dict[str, dict[str, float]]]] = {}

    for system in SYSTEMS:
        system_data = raw_results.get(system)
        if system_data is None:
            log.info("System '%s' not present in results — skipping", system)
            continue

        ragas_scores[system] = {}
        all_per_type[system] = {}

        for stage in STAGES:
            stage_data = system_data.get(stage)
            if stage_data is None:
                log.info("Stage '%s' not present for %s — skipping", stage, system)
                continue

            answers_raw: list[str] = stage_data.get("answers", [])
            if not answers_raw:
                log.info("No answers in %s/%s — skipping", system, stage)
                continue

            stage_qa_ids = stage_data.get("qa_ids") or qa_ids[: len(answers_raw)]

            scores, per_type = evaluate_stage(
                system=system,
                stage=stage,
                answers_raw=answers_raw,
                qa_index=qa_index,
                stage_qa_ids=stage_qa_ids,
                metric_names=metric_names,
            )

            if scores:
                ragas_scores[system][stage] = scores
            if per_type:
                all_per_type[system][stage] = per_type

    if not any(ragas_scores.values()):
        log.warning("No RAGAS scores were produced — nothing to write")
        return 0

    # --- Write scores back into raw JSON -----------------------------------

    raw_results["ragas_scores"] = ragas_scores
    raw_results["ragas_scores_per_type"] = all_per_type

    with open(results_path, "w", encoding="utf-8") as fh:
        json.dump(raw_results, fh, indent=2, ensure_ascii=False)
    log.info("Updated raw results: %s", results_path)

    # --- Update the markdown report ----------------------------------------

    report_path = _find_report_for_timestamp(timestamp, results_dir)
    if report_path is None:
        log.warning(
            "No matching _report.md found for timestamp '%s' in %s — "
            "skipping report update",
            timestamp,
            results_dir,
        )
    else:
        report_text = report_path.read_text(encoding="utf-8")

        # Build the RAGAS table block
        table_block = _format_scores_table(ragas_scores, metric_names)
        per_type_block = _format_per_type_table(
            {
                sys_: {
                    qtype: scores
                    for stage_data in stages.values()
                    for qtype, scores in stage_data.items()
                }
                for sys_, stages in all_per_type.items()
            },
            metric_names,
        )

        ragas_marker = "<!-- RAGAS_SCORES -->"
        ragas_section = table_block + "\n" + per_type_block

        if ragas_marker in report_text:
            # Replace existing RAGAS section between markers
            report_text = report_text.replace(
                f"{ragas_marker}\n<!-- /RAGAS_SCORES -->",
                f"{ragas_marker}\n{ragas_section}\n<!-- /RAGAS_SCORES -->",
            )
        else:
            # Append at end of file
            report_text = report_text.rstrip() + "\n\n" + ragas_section

        report_path.write_text(report_text, encoding="utf-8")
        log.info("Updated report: %s", report_path)

    # --- Print summary to stdout -------------------------------------------

    print("\n" + "=" * 60)
    print("  RAGAS Evaluation Summary")
    print("=" * 60)

    for system in SYSTEMS:
        if system not in ragas_scores:
            continue
        for stage in STAGES:
            if stage not in ragas_scores.get(system, {}):
                continue
            scores = ragas_scores[system][stage]
            print(f"\n  {system}/{stage}:")
            for m in metric_names:
                val = scores.get(m)
                if val is not None:
                    print(f"    {m:25s} {val:.4f}")

    if any(all_per_type.values()):
        print("\n  Per-type scores:")
        for system in SYSTEMS:
            for qtype in QUESTION_TYPES:
                vals = []
                for stage in STAGES:
                    pt = (
                        all_per_type.get(system, {})
                        .get(stage, {})
                        .get(qtype, {})
                    )
                    if pt:
                        vals.append(pt)
                if not vals:
                    continue
                # Average across stages for a per-type summary
                avg: dict[str, float] = {}
                for m in metric_names:
                    m_vals = [v.get(m, 0.0) for v in vals if m in v]
                    if m_vals:
                        avg[m] = sum(m_vals) / len(m_vals)
                if avg:
                    cells = "  ".join(f"{m}={avg[m]:.4f}" for m in metric_names)
                    print(f"    {system:10s} {qtype:18s} {cells}")

    print("\n" + "=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
