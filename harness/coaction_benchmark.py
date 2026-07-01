from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from harness.benchmark_runner import run_benchmark
from harness.benchmark_types import BenchmarkCase, CaseScore, Prediction
from harness.benchmarks.coaction_venue_risk import (
    DATA_ROOT,
    DEFAULT_BASELINE_CATALOG_PATH,
    DEFAULT_CASE_PACK_PATH,
    DEFAULT_EXTERNAL_REPO_CATALOG_PATH,
    DEFAULT_EXTERNAL_WRAPPER_MANIFEST_PATH,
    DEFAULT_REPORT_DIR,
    build_case_pack as build_initial_case_pack,
    load_reference_data,
    overall_judge_rows as _overall_judge_rows,
    personal_injury_overall_rows as _personal_injury_overall_rows,
    top_counties_by_metric as _top_counties_by_metric,
    top_judges_for_county as _top_judges_for_county,
    write_outputs,
)
from harness.scoring import compare_answers as _compare_answers
from harness.scoring import normalize_answers as _normalize_answers
from harness.scoring import score_predictions, summarize_suite


def run_structured_lookup(
    case: BenchmarkCase,
    reference_data: dict[str, Any],
) -> Prediction:
    from harness.baseline_runners import run_baseline_prediction

    return run_baseline_prediction(case, reference_data, "structured_lookup")


def run_baseline_prediction(
    case: BenchmarkCase,
    reference_data: dict[str, Any],
    baseline_id: str,
) -> Prediction:
    from harness.baseline_runners import run_baseline_prediction as run_prediction_impl

    return run_prediction_impl(case, reference_data, baseline_id)


def run_initial_benchmark(
    baseline_id: str = "structured_lookup",
    case_pack_path: Path = DEFAULT_CASE_PACK_PATH,
    report_dir: Path = DEFAULT_REPORT_DIR,
    baseline_catalog_path: Path = DEFAULT_BASELINE_CATALOG_PATH,
    external_repo_catalog_path: Path = DEFAULT_EXTERNAL_REPO_CATALOG_PATH,
    external_wrapper_manifest_path: Path = DEFAULT_EXTERNAL_WRAPPER_MANIFEST_PATH,
) -> dict[str, Any]:
    return run_benchmark(
        benchmark_id="coaction_venue_risk",
        baseline_id=baseline_id,
        case_pack_path=case_pack_path,
        report_dir=report_dir,
        baseline_catalog_path=baseline_catalog_path,
        external_repo_catalog_path=external_repo_catalog_path,
        external_wrapper_manifest_path=external_wrapper_manifest_path,
    )


def main() -> None:
    from harness.baseline_registry import baseline_catalog_as_json
    from harness.env_loader import load_local_env

    load_local_env()

    parser = argparse.ArgumentParser(
        description="Run the initial benchmark draft on existing Coaction venue-risk data."
    )
    parser.add_argument(
        "--baseline",
        default="structured_lookup",
        help="Baseline ID to run, or 'all' for the full suite. Use --list-baselines to inspect choices.",
    )
    parser.add_argument(
        "--case-pack-path",
        type=Path,
        default=DEFAULT_CASE_PACK_PATH,
        help="Where to write the generated case pack JSON.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=DEFAULT_REPORT_DIR,
        help="Where to write the benchmark report artifacts.",
    )
    parser.add_argument(
        "--baseline-catalog-path",
        type=Path,
        default=DEFAULT_BASELINE_CATALOG_PATH,
        help="Where to write the baseline catalog JSON.",
    )
    parser.add_argument(
        "--list-baselines",
        action="store_true",
        help="Print the currently configured baseline catalog and exit.",
    )
    args = parser.parse_args()
    if args.list_baselines:
        print(json.dumps(baseline_catalog_as_json(), indent=2))
        return
    try:
        result = run_initial_benchmark(
            baseline_id=args.baseline,
            case_pack_path=args.case_pack_path,
            report_dir=args.report_dir,
            baseline_catalog_path=args.baseline_catalog_path,
        )
    except RuntimeError as exc:
        raise SystemExit(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
