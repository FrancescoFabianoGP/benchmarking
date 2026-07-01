from __future__ import annotations

import os
from pathlib import Path
from time import perf_counter
from typing import Any

from harness.baseline_runners import run_baseline_prediction
from harness.baseline_registry import get_baseline_catalog
from harness.benchmark_registry import resolve_benchmark
from harness.scoring import score_predictions, summarize_suite


def _progress_enabled() -> bool:
    return os.getenv("BENCHMARK_PROGRESS", "").strip().lower() in {"1", "true", "yes", "on"}


def _run_cases_with_progress(
    case_pack: list[Any],
    reference_data: dict[str, Any],
    baseline_id: str,
) -> list[Any]:
    predictions = []
    total_cases = len(case_pack)
    for index, case in enumerate(case_pack, start=1):
        if _progress_enabled():
            print(
                "[benchmark] baseline={baseline} case={index}/{total} case_id={case_id} dataset={dataset} query_type={query_type}".format(
                    baseline=baseline_id,
                    index=index,
                    total=total_cases,
                    case_id=case.case_id,
                    dataset=case.dataset,
                    query_type=case.query_type,
                ),
                flush=True,
            )
        predictions.append(_run_timed_baseline(case, reference_data, baseline_id))
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
    started = perf_counter()
    prediction = run_baseline_prediction(case, reference_data, baseline_id)
    if prediction.latency_ms == 0.0:
        prediction.latency_ms = (perf_counter() - started) * 1000
    return prediction
