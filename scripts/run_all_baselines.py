from __future__ import annotations

import argparse
import math
import json
import os
import subprocess
import sys
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from pathlib import Path
from time import perf_counter
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.env_loader import load_local_env

load_local_env()

from harness.baseline_registry import get_baseline_catalog
from harness.benchmark_registry import resolve_benchmark
from harness.scoring import compare_answers
DEFAULT_REPORT_ROOT = ROOT / "reports" / "runs" / "all_baselines"


def _apply_fast_defaults() -> None:
    os.environ.setdefault("OPENAI_MODEL", "gpt-4o-mini")
    os.environ.setdefault("BENCHMARK_FRAMEWORK_MODEL", "gpt-4o-mini")
    os.environ.setdefault("LANGGRAPH_MODEL", "gpt-4o-mini")
    os.environ.setdefault("AUTOGEN_REACT_MODEL", "gpt-4o-mini")
    os.environ.setdefault("AUTOGEN_MULTI_AGENT_MODEL", "gpt-4o-mini")
    os.environ.setdefault("METAGPT_MODEL", "gpt-4o-mini")
    os.environ.setdefault("ANTHROPIC_MODEL", "claude-sonnet-4-6")


def _summary_row(result: dict[str, Any]) -> dict[str, Any]:
    summary = result.get("summary", {})
    return {
        "status": "ok",
        "runner": summary.get("runner"),
        "accuracy": summary.get("overall_accuracy"),
        "cases": summary.get("case_count"),
        "avg_latency_ms": summary.get("average_latency_ms"),
        "avg_wall_time_ms": summary.get("average_wall_time_ms"),
        "avg_cpu_time_ms": summary.get("average_cpu_time_ms"),
        "avg_io_wait_ms": summary.get("average_io_wait_ms"),
        "total_wall_time_ms": summary.get("total_wall_time_ms"),
        "total_cpu_time_ms": summary.get("total_cpu_time_ms"),
        "total_io_wait_ms": summary.get("total_io_wait_ms"),
        "total_tokens": summary.get("total_tokens"),
        "estimated_cost_usd": summary.get("total_estimated_cost_usd"),
        "report_dir": result.get("report_dir"),
    }


def _error_row(exc: Exception) -> dict[str, Any]:
    return {
        "status": "error",
        "error": str(exc),
    }


def _timeout_row(timeout_seconds: int) -> dict[str, Any]:
    return {
        "status": "timeout",
        "error": f"Timed out after {timeout_seconds} seconds",
    }


def _baseline_log_path(report_root: Path, baseline_id: str) -> Path:
    return report_root / baseline_id / "run.log"


def _analysis_report_path(report_root: Path) -> Path:
    return report_root / "gp_workflow_analysis.md"


def _scores_path(report_root: Path, baseline_id: str) -> Path:
    return report_root / baseline_id / "scores.json"


def _predictions_path(report_root: Path, baseline_id: str) -> Path:
    return report_root / baseline_id / "predictions.json"


def _load_summary_from_scores(report_root: Path, baseline_id: str) -> dict[str, Any]:
    scores_path = _scores_path(report_root, baseline_id)
    if not scores_path.exists():
        raise FileNotFoundError(f"Expected score file not found: {scores_path}")
    with scores_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return {
        "summary": payload.get("summary", {}),
        "report_dir": str(scores_path.parent),
    }


def _load_scores_payload(report_root: Path, baseline_id: str) -> dict[str, Any]:
    scores_path = _scores_path(report_root, baseline_id)
    if not scores_path.exists():
        raise FileNotFoundError(f"Expected score file not found: {scores_path}")
    with scores_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _load_predictions_payload(report_root: Path, baseline_id: str) -> list[dict[str, Any]]:
    predictions_path = _predictions_path(report_root, baseline_id)
    if not predictions_path.exists():
        raise FileNotFoundError(f"Expected predictions file not found: {predictions_path}")
    with predictions_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, list) else []


def _model_label(baseline_id: str) -> str:
    if baseline_id == "structured_lookup":
        return "deterministic lookup"
    if baseline_id in {"openai_raw_llm", "openai_with_context"}:
        return os.getenv("OPENAI_MODEL", "gpt-5")
    if baseline_id in {"anthropic_raw_llm", "anthropic_with_context"}:
        return os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    if baseline_id == "react_agent":
        return os.getenv(
            "AUTOGEN_REACT_MODEL",
            os.getenv("BENCHMARK_FRAMEWORK_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
        )
    if baseline_id == "autogen_multi_agent":
        return os.getenv(
            "AUTOGEN_MULTI_AGENT_MODEL",
            os.getenv("BENCHMARK_FRAMEWORK_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
        )
    if baseline_id == "single_agent_data_analyst":
        return os.getenv(
            "LANGGRAPH_MODEL",
            os.getenv("BENCHMARK_FRAMEWORK_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
        )
    if baseline_id in {"metagpt_sop_agent", "multi_agent_analyst_coder_critic"}:
        return os.getenv(
            "METAGPT_MODEL",
            os.getenv("BENCHMARK_FRAMEWORK_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
        )
    if baseline_id == "gp_zeus_venue_risk":
        return "zeus workflow"
    return "default"


def _progress_bar(completed: int, total: int, width: int = 24) -> str:
    if total <= 0:
        return "[" + ("-" * width) + "]"
    filled = int(width * completed / total)
    if filled > width:
        filled = width
    return "[" + ("#" * filled) + ("-" * (width - filled)) + "]"


def _print_baseline_banner(index: int, total: int, baseline_id: str, model: str) -> None:
    banner = (
        "================ baseline {index}/{total}: {baseline} | model: {model} ================".format(
            index=index,
            total=total,
            baseline=baseline_id,
            model=model,
        )
    )
    print(banner, flush=True)


def _print_suite_progress(rows: dict[str, dict[str, Any]], total: int) -> None:
    _print_suite_progress_with_eta(rows, total, 0.0, 1, {}, 0)


def _format_seconds(seconds: float) -> str:
    return f"{seconds:.1f}s"


def _ordered_rows(
    baseline_ids: list[str],
    rows: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {baseline_id: rows[baseline_id] for baseline_id in baseline_ids if baseline_id in rows}


def _print_running_snapshot(running_details: dict[str, dict[str, Any]]) -> None:
    if not running_details:
        print("[suite-running] none", flush=True)
        return
    for baseline_id, details in sorted(
        running_details.items(),
        key=lambda item: (int(item[1]["slot"]), float(item[1]["started_at"])),
    ):
        print(
            "[suite-running] slot={slot} baseline={baseline} model={model} elapsed={elapsed} log={log_path}".format(
                slot=details["slot"],
                baseline=baseline_id,
                model=details["model"],
                elapsed=_format_seconds(perf_counter() - float(details["started_at"])),
                log_path=details["log_path"],
            ),
            flush=True,
        )


def _print_suite_progress_with_eta(
    rows: dict[str, dict[str, Any]],
    total: int,
    elapsed_seconds: float,
    max_parallel_baselines: int,
    running_details: dict[str, dict[str, Any]],
    queued_count: int,
) -> None:
    completed = len(rows)
    ok = sum(1 for row in rows.values() if row.get("status") == "ok")
    errors = sum(1 for row in rows.values() if row.get("status") == "error")
    timeouts = sum(1 for row in rows.values() if row.get("status") == "timeout")
    percent = (completed / total) * 100 if total else 0.0
    average_baseline_seconds = (elapsed_seconds / completed) if completed else 0.0
    remaining = max(0, total - completed)
    batches_remaining = (
        math.ceil(remaining / max(1, max_parallel_baselines)) if remaining else 0
    )
    eta_seconds = average_baseline_seconds * batches_remaining
    running_label = ",".join(sorted(running_details)) if running_details else "-"
    print(
        "[suite-progress] {bar} {completed}/{total} complete ({percent:.1f}%) ok={ok} error={errors} timeout={timeouts} running={running_count} queued={queued_count} running_baselines={running_label} elapsed={elapsed} eta={eta}".format(
            bar=_progress_bar(completed, total),
            completed=completed,
            total=total,
            percent=percent,
            ok=ok,
            errors=errors,
            timeouts=timeouts,
            running_count=len(running_details),
            queued_count=queued_count,
            running_label=running_label,
            elapsed=_format_seconds(elapsed_seconds),
            eta=_format_seconds(eta_seconds),
        ),
        flush=True,
    )


def _write_outputs(report_root: Path, benchmark_id: str, rows: dict[str, dict[str, Any]]) -> None:
    report_root.mkdir(parents=True, exist_ok=True)
    catalog = {spec.baseline_id: spec for spec in get_baseline_catalog()}
    payload = {
        "benchmark_id": benchmark_id,
        "baselines": rows,
    }
    with (report_root / "suite_status.json").open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    lines = [
        "# Baseline Suite Status",
        "",
        f"- Benchmark: `{benchmark_id}`",
        "",
        "| Baseline | Status | Accuracy | Avg Latency (ms) | Avg Wall (ms) | Avg CPU (ms) | Avg I/O Wait (ms) | Total Wall (ms) | Total CPU (ms) | Total I/O Wait (ms) | Tokens | Est. Cost (USD) | Notes |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for baseline_id, row in rows.items():
        if row["status"] == "ok":
            lines.append(
                "| {baseline_id} | ok | {accuracy} | {latency} | {wall} | {cpu} | {io} | {total_wall} | {total_cpu} | {total_io} | {tokens} | {cost} | {report_dir} |".format(
                    baseline_id=baseline_id,
                    accuracy=f"{row['accuracy']:.1%}" if isinstance(row.get("accuracy"), (int, float)) else "n/a",
                    latency=f"{row['avg_latency_ms']:.2f}" if isinstance(row.get("avg_latency_ms"), (int, float)) else "n/a",
                    wall=f"{row['avg_wall_time_ms']:.2f}" if isinstance(row.get("avg_wall_time_ms"), (int, float)) else "n/a",
                    cpu=f"{row['avg_cpu_time_ms']:.2f}" if isinstance(row.get("avg_cpu_time_ms"), (int, float)) else "n/a",
                    io=f"{row['avg_io_wait_ms']:.2f}" if isinstance(row.get("avg_io_wait_ms"), (int, float)) else "n/a",
                    total_wall=f"{row['total_wall_time_ms']:.2f}" if isinstance(row.get("total_wall_time_ms"), (int, float)) else "n/a",
                    total_cpu=f"{row['total_cpu_time_ms']:.2f}" if isinstance(row.get("total_cpu_time_ms"), (int, float)) else "n/a",
                    total_io=f"{row['total_io_wait_ms']:.2f}" if isinstance(row.get("total_io_wait_ms"), (int, float)) else "n/a",
                    tokens=row.get("total_tokens", "n/a") if row.get("total_tokens") is not None else "n/a",
                    cost=f"{row['estimated_cost_usd']:.6f}" if isinstance(row.get("estimated_cost_usd"), (int, float)) else "n/a",
                    report_dir=row.get("report_dir", ""),
                )
            )
        else:
            lines.append(
                f"| {baseline_id} | error | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | {str(row.get('error', '')).replace('|', '/')} |"
            )

    lines.extend(
        [
            "",
            "## Method Summary",
            "",
            "| Baseline | Method | Category | Paper | Quick Description |",
            "|---|---|---|---|---|",
        ]
    )
    for baseline_id in rows:
        spec = catalog.get(baseline_id)
        if spec is None:
            lines.append(f"| {baseline_id} | n/a | n/a | n/a | n/a |")
            continue
        paper_cell = (
            f"[{spec.paper_title}]({spec.paper_url})"
            if spec.paper_title and spec.paper_url
            else "n/a"
        )
        lines.append(
            "| {baseline_id} | {label} | {category} | {paper} | {description} |".format(
                baseline_id=baseline_id,
                label=spec.label.replace("|", "/"),
                category=spec.category.replace("|", "/"),
                paper=paper_cell.replace("|", "/"),
                description=spec.description.replace("|", "/"),
            )
        )

    with (report_root / "suite_status.md").open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def _safe_ratio(numerator: float | int | None, denominator: float | int | None) -> float | None:
    if not isinstance(numerator, (int, float)) or not isinstance(denominator, (int, float)):
        return None
    if denominator == 0:
        return None
    return float(numerator) / float(denominator)


def _format_percent(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.1%}"
    return "n/a"


def _format_ms(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.2f}"
    return "n/a"


def _format_cost(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.6f}"
    return "n/a"


def _likely_failure_reason(expected: list[str], predicted: list[str]) -> str:
    if not predicted:
        return "No answer returned."
    predicted_set = {item.strip() for item in predicted}
    expected_set = {item.strip() for item in expected}
    if "All Counties" in predicted_set or "All Courts" in predicted_set:
        return "Included an aggregate row in the answer instead of restricting to county-level winners."
    if expected_set and expected_set.issubset(predicted_set) and predicted_set != expected_set:
        return "Over-returned answers; the workflow included extra candidates beyond the benchmark gold answer."
    if len(predicted_set) > len(expected_set):
        return "Returned a broader set of answers than expected, suggesting ambiguity handling or ranking leakage."
    return "Selected the wrong top-ranked answer for this case."


def _write_gp_analysis_report(
    report_root: Path,
    benchmark_id: str,
    rows: dict[str, dict[str, Any]],
) -> None:
    target_baseline = "gp_zeus_venue_risk"
    output_path = _analysis_report_path(report_root)
    catalog = {spec.baseline_id: spec for spec in get_baseline_catalog()}
    if target_baseline not in rows:
        output_path.write_text(
            "# GP Workflow Comparative Analysis\n\nGP Zeus baseline was not included in this suite run.\n",
            encoding="utf-8",
        )
        return

    spec = resolve_benchmark(benchmark_id)
    reference_data = spec.load_reference_data()
    case_pack = spec.build_case_pack(reference_data)
    case_by_id = {case.case_id: case for case in case_pack}

    successful_rows = {
        baseline_id: row for baseline_id, row in rows.items() if row.get("status") == "ok"
    }
    comparable_successful_rows = {
        baseline_id: row
        for baseline_id, row in successful_rows.items()
        if baseline_id == target_baseline
        or (
            catalog.get(baseline_id) is not None
            and catalog[baseline_id].category != "deterministic_reference"
        )
    }
    failed_rows = {
        baseline_id: row for baseline_id, row in rows.items() if row.get("status") != "ok"
    }

    summaries: dict[str, dict[str, Any]] = {}
    predictions_by_baseline: dict[str, list[dict[str, Any]]] = {}
    correctness_by_baseline: dict[str, dict[str, bool]] = {}
    for baseline_id in comparable_successful_rows:
        try:
            summaries[baseline_id] = _load_scores_payload(report_root, baseline_id).get("summary", {})
            predictions = _load_predictions_payload(report_root, baseline_id)
        except FileNotFoundError:
            continue
        predictions_by_baseline[baseline_id] = predictions
        correctness_by_baseline[baseline_id] = {
            pred["case_id"]: compare_answers(case_by_id[pred["case_id"]].gold_answer, pred.get("answer", []))
            for pred in predictions
            if pred.get("case_id") in case_by_id
        }

    gp_row = rows[target_baseline]
    gp_summary = summaries.get(target_baseline, {})
    gp_predictions = predictions_by_baseline.get(target_baseline, [])
    gp_correctness = correctness_by_baseline.get(target_baseline, {})
    gp_accuracy_rank = "n/a"
    gp_speed_rank = "n/a"

    ranked_by_accuracy = sorted(
        comparable_successful_rows.items(),
        key=lambda item: (
            -(float(item[1]["accuracy"])) if isinstance(item[1].get("accuracy"), (int, float)) else float("inf"),
            float(item[1].get("avg_wall_time_ms", float("inf"))) if isinstance(item[1].get("avg_wall_time_ms"), (int, float)) else float("inf"),
            item[0],
        ),
    )
    for index, (baseline_id, _) in enumerate(ranked_by_accuracy, start=1):
        if baseline_id == target_baseline:
            gp_accuracy_rank = f"{index}/{len(ranked_by_accuracy)}"
            break

    ranked_by_speed = sorted(
        comparable_successful_rows.items(),
        key=lambda item: (
            float(item[1].get("avg_wall_time_ms", float("inf"))) if isinstance(item[1].get("avg_wall_time_ms"), (int, float)) else float("inf"),
            -(float(item[1]["accuracy"])) if isinstance(item[1].get("accuracy"), (int, float)) else float("inf"),
            item[0],
        ),
    )
    for index, (baseline_id, _) in enumerate(ranked_by_speed, start=1):
        if baseline_id == target_baseline:
            gp_speed_rank = f"{index}/{len(ranked_by_speed)}"
            break

    best_accuracy_row = ranked_by_accuracy[0][1] if ranked_by_accuracy else {}
    fastest_row = ranked_by_speed[0][1] if ranked_by_speed else {}
    fastest_comparable_row = ranked_by_speed[0][1] if ranked_by_speed else fastest_row
    best_accuracy_gap = None
    if isinstance(gp_row.get("accuracy"), (int, float)) and isinstance(best_accuracy_row.get("accuracy"), (int, float)):
        best_accuracy_gap = float(best_accuracy_row["accuracy"]) - float(gp_row["accuracy"])
    speed_ratio = _safe_ratio(gp_row.get("avg_wall_time_ms"), fastest_comparable_row.get("avg_wall_time_ms"))

    strengths: list[str] = []
    weaknesses: list[str] = []

    gp_query = gp_summary.get("by_query_type", {})
    if isinstance(gp_query, dict):
        for query_type, data in gp_query.items():
            if not isinstance(data, dict):
                continue
            gp_query_acc = data.get("accuracy")
            competitor_max = max(
                (
                    summary.get("by_query_type", {}).get(query_type, {}).get("accuracy")
                    for baseline_id, summary in summaries.items()
                    if baseline_id != target_baseline
                ),
                default=None,
            )
            if isinstance(gp_query_acc, (int, float)) and isinstance(competitor_max, (int, float)):
                if gp_query_acc >= competitor_max:
                    strengths.append(
                        f"Matched or led the field on `{query_type}` questions at {_format_percent(gp_query_acc)}."
                    )
                elif competitor_max - gp_query_acc >= 0.10:
                    weaknesses.append(
                        f"Trailed the strongest baselines on `{query_type}` questions by {_format_percent(competitor_max - gp_query_acc)}."
                    )

    gp_dataset = gp_summary.get("by_dataset", {})
    if isinstance(gp_dataset, dict):
        for dataset, data in gp_dataset.items():
            if not isinstance(data, dict):
                continue
            gp_dataset_acc = data.get("accuracy")
            competitor_max = max(
                (
                    summary.get("by_dataset", {}).get(dataset, {}).get("accuracy")
                    for baseline_id, summary in summaries.items()
                    if baseline_id != target_baseline
                ),
                default=None,
            )
            if isinstance(gp_dataset_acc, (int, float)) and gp_dataset_acc == 1.0:
                strengths.append(f"Was perfect on the `{dataset}` slice.")
            elif isinstance(gp_dataset_acc, (int, float)) and isinstance(competitor_max, (int, float)):
                if competitor_max - gp_dataset_acc >= 0.10:
                    weaknesses.append(
                        f"Underperformed on `{dataset}` cases by {_format_percent(competitor_max - gp_dataset_acc)} versus the best comparator."
                    )

    if isinstance(speed_ratio, float) and speed_ratio > 1.5:
        weaknesses.append(
            f"Was materially slower than the fastest comparable live baseline: about {speed_ratio:.1f}x slower on average wall time."
        )
    if isinstance(best_accuracy_gap, float) and best_accuracy_gap > 0:
        weaknesses.append(
            f"Finished {_format_percent(best_accuracy_gap)} behind the best accuracy achieved in this run."
        )

    raw_llm_rows = [
        row for baseline_id, row in successful_rows.items() if baseline_id in {"openai_raw_llm", "anthropic_raw_llm"}
    ]
    if raw_llm_rows and isinstance(gp_row.get("accuracy"), (int, float)):
        raw_best = max(float(row["accuracy"]) for row in raw_llm_rows if isinstance(row.get("accuracy"), (int, float)))
        if gp_row["accuracy"] > raw_best:
            strengths.append(
                f"Clearly beat the raw LLM baselines, which topped out at {_format_percent(raw_best)}."
            )

    failed_case_lines: list[str] = []
    gp_wrong_predictions = []
    for pred in gp_predictions:
        case_id = pred.get("case_id")
        if case_id not in case_by_id:
            continue
        if gp_correctness.get(case_id):
            continue
        gp_wrong_predictions.append(pred)

    for pred in gp_wrong_predictions:
        case = case_by_id[pred["case_id"]]
        successful_correct = [
            baseline_id
            for baseline_id, case_correctness in correctness_by_baseline.items()
            if baseline_id != target_baseline and case_correctness.get(pred["case_id"])
        ]
        failed_case_lines.append(
            "- `{case_id}` ({dataset}, `{query_type}`): expected `{expected}`, GP returned `{predicted}`. Likely cause: {reason} Other successful baselines that got it right: {others}.".format(
                case_id=pred["case_id"],
                dataset=case.dataset,
                query_type=case.query_type,
                expected=", ".join(case.gold_answer) or "n/a",
                predicted=", ".join(pred.get("answer", [])) or "n/a",
                reason=_likely_failure_reason(case.gold_answer, pred.get("answer", [])),
                others=", ".join(successful_correct) if successful_correct else "none",
            )
        )

    failure_context_lines: list[str] = []
    for baseline_id, row in failed_rows.items():
        if baseline_id == target_baseline:
            continue
        failure_context_lines.append(
            "- `{baseline}`: `{status}`. See `{log_path}`. {details}".format(
                baseline=baseline_id,
                status=row.get("status", "error"),
                log_path=_baseline_log_path(report_root, baseline_id),
                details=str(row.get("error", "no details"))[:240],
            )
        )

    comparison_lines = [
        "| Baseline | Status | Accuracy | Avg Wall (ms) | Avg CPU (ms) | Est. Cost (USD) |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for baseline_id, row in sorted(
        comparable_successful_rows.items(),
        key=lambda item: (
            0 if item[0] == target_baseline else 1,
            -float(item[1]["accuracy"]) if isinstance(item[1].get("accuracy"), (int, float)) else float("-inf"),
            item[0],
        ),
    ):
        comparison_lines.append(
            "| {baseline} | {status} | {accuracy} | {wall} | {cpu} | {cost} |".format(
                baseline=baseline_id,
                status=row.get("status", "n/a"),
                accuracy=_format_percent(row.get("accuracy")),
                wall=_format_ms(row.get("avg_wall_time_ms")),
                cpu=_format_ms(row.get("avg_cpu_time_ms")),
                cost=_format_cost(row.get("estimated_cost_usd")),
            )
        )

    lines = [
        "# GP Workflow Comparative Analysis",
        "",
        f"- Benchmark: `{benchmark_id}`",
        f"- Target baseline: `{target_baseline}`",
        f"- GP accuracy rank among successful non-reference baselines: `{gp_accuracy_rank}`",
        f"- GP speed rank by average wall time among successful non-reference baselines: `{gp_speed_rank}`",
        "",
        "## Snapshot",
        "",
        "| Metric | GP Zeus | Best In Run |",
        "|---|---:|---:|",
        f"| Overall accuracy | {_format_percent(gp_row.get('accuracy'))} | {_format_percent(best_accuracy_row.get('accuracy'))} |",
        f"| Avg wall time (ms) | {_format_ms(gp_row.get('avg_wall_time_ms'))} | {_format_ms(fastest_comparable_row.get('avg_wall_time_ms'))} |",
        f"| Avg CPU time (ms) | {_format_ms(gp_row.get('avg_cpu_time_ms'))} | {_format_ms(min((row.get('avg_cpu_time_ms') for row in comparable_successful_rows.values() if isinstance(row.get('avg_cpu_time_ms'), (int, float))), default=None))} |",
        f"| Estimated cost (USD) | {_format_cost(gp_row.get('estimated_cost_usd'))} | {_format_cost(min((row.get('estimated_cost_usd') for row in comparable_successful_rows.values() if isinstance(row.get('estimated_cost_usd'), (int, float))), default=None))} |",
        "",
        "## GP Vs Others",
        "",
        *comparison_lines,
        "",
        "## Strengths",
        "",
    ]

    if strengths:
        lines.extend(strengths if all(item.startswith("- ") for item in strengths) else [f"- {item}" for item in strengths])
    else:
        lines.append("- No standout GP-specific strength was automatically identified from this run beyond its raw accuracy.")

    lines.extend(["", "## Weaknesses", ""])
    if weaknesses:
        lines.extend(weaknesses if all(item.startswith("- ") for item in weaknesses) else [f"- {item}" for item in weaknesses])
    else:
        lines.append("- No major GP-specific weakness was automatically identified from this run.")

    lines.extend(["", "## Failure Analysis", ""])
    if failed_case_lines:
        lines.extend(failed_case_lines)
    else:
        lines.append("- GP Zeus did not miss any cases in this run.")

    lines.extend(["", "## Execution Context", ""])
    if failure_context_lines:
        lines.append("Some comparator baselines failed to execute, which matters when interpreting GP's rank:")
        lines.extend(failure_context_lines)
    else:
        lines.append("- All baselines completed successfully in this run.")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run registered baselines, optionally in parallel, and keep going on failures."
    )
    parser.add_argument("--benchmark", default="coaction_venue_risk")
    parser.add_argument("--baseline", action="append", help="Optional baseline IDs to run.")
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=600,
        help="Per-baseline timeout in seconds.",
    )
    parser.add_argument(
        "--profile",
        choices=["fast", "current"],
        default="fast",
        help="Use fast model defaults unless explicit environment variables already override them.",
    )
    parser.add_argument(
        "--max-parallel-baselines",
        type=int,
        default=0,
        help="Maximum number of baselines to run concurrently. Use 0 to run all at once.",
    )
    parser.add_argument(
        "--progress-interval-seconds",
        type=float,
        default=5.0,
        help="How often to print suite heartbeats while waiting for running baselines.",
    )
    return parser.parse_args()


def _run_single_baseline(
    benchmark_id: str,
    baseline_id: str,
    report_root: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    report_dir = report_root / baseline_id
    log_path = _baseline_log_path(report_root, baseline_id)
    report_dir.mkdir(parents=True, exist_ok=True)

    child_env = os.environ.copy()
    child_env.setdefault("BENCHMARK_PROGRESS", "1")
    started = perf_counter()
    try:
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "run_benchmark.py"),
                "--benchmark",
                benchmark_id,
                "--baseline",
                baseline_id,
                "--report-dir",
                str(report_dir),
            ],
            cwd=ROOT,
            env=child_env,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=True,
        )
        log_path.write_text((completed.stdout or "") + (completed.stderr or ""), encoding="utf-8")
        result = _load_summary_from_scores(report_root, baseline_id)
        row = _summary_row(result)
        row["elapsed_seconds"] = perf_counter() - started
        row["log_path"] = str(log_path)
        return row
    except subprocess.TimeoutExpired as exc:
        log_path.write_text((exc.stdout or "") + (exc.stderr or ""), encoding="utf-8")
        row = _timeout_row(timeout_seconds)
        row["elapsed_seconds"] = perf_counter() - started
        row["log_path"] = str(log_path)
        return row
    except subprocess.CalledProcessError as exc:
        log_path.write_text((exc.stdout or "") + (exc.stderr or ""), encoding="utf-8")
        row = {
            "status": "error",
            "error": str(exc),
            "elapsed_seconds": perf_counter() - started,
            "log_path": str(log_path),
        }
        return row
    except Exception as exc:  # noqa: BLE001
        log_path.write_text(str(exc), encoding="utf-8")
        row = _error_row(exc)
        row["elapsed_seconds"] = perf_counter() - started
        row["log_path"] = str(log_path)
        return row


def main() -> None:
    args = parse_args()
    if args.profile == "fast":
        _apply_fast_defaults()

    baseline_ids = (
        args.baseline
        if args.baseline
        else [spec.baseline_id for spec in get_baseline_catalog()]
    )

    rows: dict[str, dict[str, Any]] = {}
    total = len(baseline_ids)
    max_parallel = args.max_parallel_baselines if args.max_parallel_baselines > 0 else total
    max_parallel = max(1, min(max_parallel, total))
    suite_started = perf_counter()
    print(
        "[suite] using max_parallel_baselines={max_parallel} progress_interval_seconds={progress_interval:.1f}".format(
            max_parallel=max_parallel,
            progress_interval=args.progress_interval_seconds,
        ),
        flush=True,
    )
    running_details: dict[str, dict[str, Any]] = {}
    future_to_baseline: dict[Future[dict[str, Any]], str] = {}
    next_to_submit = 0

    with ThreadPoolExecutor(max_workers=max_parallel) as executor:
        while next_to_submit < total or future_to_baseline:
            while next_to_submit < total and len(future_to_baseline) < max_parallel:
                baseline_id = baseline_ids[next_to_submit]
                report_dir = args.report_root / baseline_id
                model_label = _model_label(baseline_id)
                slot = len(running_details) + 1
                log_path = _baseline_log_path(args.report_root, baseline_id)
                _print_baseline_banner(next_to_submit + 1, total, baseline_id, model_label)
                print(
                    "[suite] launching slot={slot} index={index}/{total} baseline={baseline} model={model} active={active_count}/{max_parallel} queued_after_launch={queued_count} report_dir={report_dir} log={log_path}".format(
                        slot=slot,
                        index=next_to_submit + 1,
                        total=total,
                        baseline=baseline_id,
                        model=model_label,
                        active_count=len(running_details) + 1,
                        max_parallel=max_parallel,
                        queued_count=max(0, total - (next_to_submit + 1) - len(rows) - len(running_details)),
                        report_dir=report_dir,
                        log_path=log_path,
                    ),
                    flush=True,
                )
                future = executor.submit(
                    _run_single_baseline,
                    args.benchmark,
                    baseline_id,
                    args.report_root,
                    args.timeout_seconds,
                )
                future_to_baseline[future] = baseline_id
                running_details[baseline_id] = {
                    "slot": slot,
                    "model": model_label,
                    "started_at": perf_counter(),
                    "log_path": str(log_path),
                }
                next_to_submit += 1

            done, _ = wait(
                future_to_baseline.keys(),
                timeout=max(0.1, args.progress_interval_seconds),
                return_when=FIRST_COMPLETED,
            )
            if not done:
                _print_suite_progress_with_eta(
                    rows,
                    total,
                    perf_counter() - suite_started,
                    max_parallel,
                    running_details,
                    max(0, total - len(rows) - len(running_details)),
                )
                _print_running_snapshot(running_details)
                continue
            for future in done:
                baseline_id = future_to_baseline.pop(future)
                launch_details = running_details.pop(baseline_id, {})
                rows[baseline_id] = future.result()
                summary = rows[baseline_id]
                if summary["status"] == "ok":
                    print(
                        "[suite] completed slot={slot} baseline={baseline} status=ok elapsed={elapsed} accuracy={accuracy} avg_latency_ms={latency} avg_wall_ms={wall} avg_cpu_ms={cpu} avg_io_wait_ms={io} active_remaining={active_remaining} queued_remaining={queued_remaining} log={log_path}".format(
                            slot=launch_details.get("slot", "?"),
                            baseline=baseline_id,
                            elapsed=_format_seconds(float(summary.get("elapsed_seconds", 0.0))),
                            accuracy=(
                                f"{summary['accuracy']:.1%}"
                                if isinstance(summary.get("accuracy"), (int, float))
                                else "n/a"
                            ),
                            latency=(
                                f"{summary['avg_latency_ms']:.2f}"
                                if isinstance(summary.get("avg_latency_ms"), (int, float))
                                else "n/a"
                            ),
                            wall=(
                                f"{summary['avg_wall_time_ms']:.2f}"
                                if isinstance(summary.get("avg_wall_time_ms"), (int, float))
                                else "n/a"
                            ),
                            cpu=(
                                f"{summary['avg_cpu_time_ms']:.2f}"
                                if isinstance(summary.get("avg_cpu_time_ms"), (int, float))
                                else "n/a"
                            ),
                            io=(
                                f"{summary['avg_io_wait_ms']:.2f}"
                                if isinstance(summary.get("avg_io_wait_ms"), (int, float))
                                else "n/a"
                            ),
                            active_remaining=len(running_details),
                            queued_remaining=max(0, total - len(rows) - len(running_details)),
                            log_path=summary.get("log_path", ""),
                        ),
                        flush=True,
                    )
                else:
                    print(
                        "[suite] completed slot={slot} baseline={baseline} status={status} elapsed={elapsed} active_remaining={active_remaining} queued_remaining={queued_remaining} details={details} log={log_path}".format(
                            slot=launch_details.get("slot", "?"),
                            baseline=baseline_id,
                            status=summary["status"],
                            elapsed=_format_seconds(float(summary.get("elapsed_seconds", 0.0))),
                            active_remaining=len(running_details),
                            queued_remaining=max(0, total - len(rows) - len(running_details)),
                            details=summary.get("error", ""),
                            log_path=summary.get("log_path", ""),
                        ),
                        flush=True,
                    )
                partial_rows = _ordered_rows(baseline_ids, rows)
                _write_outputs(args.report_root, args.benchmark, partial_rows)
                _write_gp_analysis_report(args.report_root, args.benchmark, partial_rows)
                _print_suite_progress_with_eta(
                    rows,
                    total,
                    perf_counter() - suite_started,
                    max_parallel,
                    running_details,
                    max(0, total - len(rows) - len(running_details)),
                )
                _print_running_snapshot(running_details)

    ordered_rows = _ordered_rows(baseline_ids, rows)
    _write_outputs(args.report_root, args.benchmark, ordered_rows)
    _write_gp_analysis_report(args.report_root, args.benchmark, ordered_rows)
    print(json.dumps({"benchmark_id": args.benchmark, "baselines": ordered_rows}, indent=2))


if __name__ == "__main__":
    main()
