from __future__ import annotations

import os
import resource
from pathlib import Path
from time import perf_counter
from typing import Any

from harness.baseline_runners import run_baseline_prediction
from harness.baseline_registry import get_baseline_catalog
from harness.benchmark_registry import resolve_benchmark
from harness.scoring import score_predictions, summarize_suite


def _progress_enabled() -> bool:
    return os.getenv("BENCHMARK_PROGRESS", "").strip().lower() in {"1", "true", "yes", "on"}


def _progress_bar(completed: int, total: int, width: int = 18) -> str:
    if total <= 0:
        return "[" + ("-" * width) + "]"
    filled = int(width * completed / total)
    if filled > width:
        filled = width
    return "[" + ("#" * filled) + ("-" * (width - filled)) + "]"


def _format_seconds(seconds: float) -> str:
    return f"{seconds:.1f}s"


def _cpu_snapshot_ms() -> float:
    self_usage = resource.getrusage(resource.RUSAGE_SELF)
    child_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return (
        self_usage.ru_utime
        + self_usage.ru_stime
        + child_usage.ru_utime
        + child_usage.ru_stime
    ) * 1000.0


def _run_cases_with_progress(
    case_pack: list[Any],
    reference_data: dict[str, Any],
    baseline_id: str,
) -> list[Any]:
    predictions = []
    total_cases = len(case_pack)
    baseline_started = perf_counter()
    for index, case in enumerate(case_pack, start=1):
        if _progress_enabled():
            print(
                "[benchmark] baseline={baseline} {bar} case={index}/{total} case_id={case_id} dataset={dataset} query_type={query_type}".format(
                    baseline=baseline_id,
                    bar=_progress_bar(index - 1, total_cases),
                    index=index,
                    total=total_cases,
                    case_id=case.case_id,
                    dataset=case.dataset,
                    query_type=case.query_type,
                ),
                flush=True,
            )
        prediction = _run_timed_baseline(case, reference_data, baseline_id)
        predictions.append(prediction)
        if _progress_enabled():
            elapsed_seconds = perf_counter() - baseline_started
            average_case_seconds = elapsed_seconds / index
            remaining_cases = total_cases - index
            eta_seconds = average_case_seconds * remaining_cases
            print(
                "[benchmark-progress] baseline={baseline} {bar} completed={completed}/{total} wall={wall:.1f}ms cpu={cpu:.1f}ms io_wait={io:.1f}ms elapsed={elapsed} eta={eta}".format(
                    baseline=baseline_id,
                    bar=_progress_bar(index, total_cases),
                    completed=index,
                    total=total_cases,
                    wall=prediction.wall_time_ms,
                    cpu=prediction.cpu_time_ms,
                    io=prediction.io_wait_ms,
                    elapsed=_format_seconds(elapsed_seconds),
                    eta=_format_seconds(eta_seconds),
                ),
                flush=True,
            )
    return predictions


def run_benchmark(
    benchmark_id: str,
    baseline_id: str = "structured_lookup",
    case_pack_path: Path | None = None,
    report_dir: Path | None = None,
    baseline_catalog_path: Path | None = None,
    external_repo_catalog_path: Path | None = None,
    external_wrapper_manifest_path: Path | None = None,
) -> dict[str, Any]:
    spec = resolve_benchmark(benchmark_id)
    effective_case_pack_path = case_pack_path or spec.default_case_pack_path
    effective_report_dir = report_dir or spec.default_report_dir
    effective_baseline_catalog_path = baseline_catalog_path or spec.default_baseline_catalog_path
    effective_external_repo_catalog_path = (
        external_repo_catalog_path or spec.default_external_repo_catalog_path
    )
    effective_external_wrapper_manifest_path = (
        external_wrapper_manifest_path or spec.default_external_wrapper_manifest_path
    )

    reference_data = spec.load_reference_data()
    case_pack = spec.build_case_pack(reference_data)
    if baseline_id == "all":
        baseline_ids = [baseline.baseline_id for baseline in get_baseline_catalog()]
    else:
        baseline_ids = [baseline_id]

    predictions_by_baseline = {
        current_baseline: _run_cases_with_progress(case_pack, reference_data, current_baseline)
        for current_baseline in baseline_ids
    }
    active_predictions = predictions_by_baseline[baseline_ids[0]]
    scores, summary = score_predictions(case_pack, active_predictions)
    suite_summary = summarize_suite(case_pack, predictions_by_baseline)
    spec.write_outputs(
        case_pack,
        active_predictions,
        scores,
        summary,
        effective_case_pack_path,
        effective_report_dir,
        effective_baseline_catalog_path,
        suite_summary=suite_summary,
        predictions_by_baseline=predictions_by_baseline,
        external_repo_catalog_path=effective_external_repo_catalog_path,
        external_wrapper_manifest_path=effective_external_wrapper_manifest_path,
    )
    return {
        "benchmark_id": benchmark_id,
        "baseline_id": baseline_id,
        "executed_baselines": baseline_ids,
        "case_pack_path": str(effective_case_pack_path),
        "baseline_catalog_path": str(effective_baseline_catalog_path),
        "external_repo_catalog_path": str(effective_external_repo_catalog_path),
        "external_wrapper_manifest_path": str(effective_external_wrapper_manifest_path),
        "report_dir": str(effective_report_dir),
        "summary": summary,
        "suite_summary": suite_summary,
    }


def _run_timed_baseline(case: Any, reference_data: dict[str, Any], baseline_id: str) -> Any:
    cpu_started_ms = _cpu_snapshot_ms()
    started = perf_counter()
    prediction = run_baseline_prediction(case, reference_data, baseline_id)
    wall_time_ms = (perf_counter() - started) * 1000
    cpu_time_ms = max(0.0, _cpu_snapshot_ms() - cpu_started_ms)
    prediction.wall_time_ms = wall_time_ms
    prediction.cpu_time_ms = cpu_time_ms
    prediction.io_wait_ms = max(0.0, wall_time_ms - cpu_time_ms)
    if prediction.latency_ms == 0.0:
        prediction.latency_ms = wall_time_ms
    return prediction
