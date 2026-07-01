from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.env_loader import load_local_env

load_local_env()

import argparse

from harness.baseline_registry import baseline_catalog_as_json
from harness.benchmark_registry import benchmark_catalog_as_json, resolve_benchmark
from harness.benchmark_runner import run_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a registered benchmark against one baseline or the full suite."
    )
    parser.add_argument(
        "--benchmark",
        default="coaction_venue_risk",
        help="Benchmark ID to run. Use --list-benchmarks to inspect choices.",
    )
    parser.add_argument(
        "--baseline",
        default="structured_lookup",
        help="Baseline ID to run, or 'all' for the full suite. Use --list-baselines to inspect choices.",
    )
    parser.add_argument(
        "--case-pack-path",
        type=Path,
        help="Where to write the generated case pack JSON.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        help="Where to write the benchmark report artifacts.",
    )
    parser.add_argument(
        "--baseline-catalog-path",
        type=Path,
        help="Where to write the baseline catalog JSON.",
    )
    parser.add_argument(
        "--external-repo-catalog-path",
        type=Path,
        help="Where to write the external repo catalog JSON.",
    )
    parser.add_argument(
        "--external-wrapper-manifest-path",
        type=Path,
        help="Where to write the external wrapper manifest JSON.",
    )
    parser.add_argument(
        "--list-baselines",
        action="store_true",
        help="Print the currently configured baseline catalog and exit.",
    )
    parser.add_argument(
        "--list-benchmarks",
        action="store_true",
        help="Print the currently registered benchmarks and exit.",
    )
    args = parser.parse_args()

    if args.list_baselines:
        print(json.dumps(baseline_catalog_as_json(), indent=2))
        return
    if args.list_benchmarks:
        print(json.dumps(benchmark_catalog_as_json(), indent=2, default=str))
        return

    try:
        resolve_benchmark(args.benchmark)
        result = run_benchmark(
            benchmark_id=args.benchmark,
            baseline_id=args.baseline,
            case_pack_path=args.case_pack_path,
            report_dir=args.report_dir,
            baseline_catalog_path=args.baseline_catalog_path,
            external_repo_catalog_path=args.external_repo_catalog_path,
            external_wrapper_manifest_path=args.external_wrapper_manifest_path,
        )
    except RuntimeError as exc:
        raise SystemExit(str(exc))
    except ValueError as exc:
        raise SystemExit(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
