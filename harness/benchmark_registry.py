from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from harness.benchmark_types import BenchmarkCase, CaseScore, Prediction


@dataclass(frozen=True)
class BenchmarkSpec:
    benchmark_id: str
    label: str
    description: str
    default_case_pack_path: Path
    default_report_dir: Path
    default_baseline_catalog_path: Path
    default_external_repo_catalog_path: Path
    default_external_wrapper_manifest_path: Path
    load_reference_data: Callable[[], dict[str, Any]]
    build_case_pack: Callable[[dict[str, Any]], list[BenchmarkCase]]
    write_outputs: Callable[
        [
            list[BenchmarkCase],
            list[Prediction],
            list[CaseScore],
            dict[str, Any],
            Path,
            Path,
            Path,
            dict[str, Any] | None,
            dict[str, list[Prediction]] | None,
            Path | None,
            Path | None,
        ],
        None,
    ]


def get_benchmark_catalog() -> list[BenchmarkSpec]:
    from harness.benchmarks.coaction_venue_risk import COACTION_VENUE_RISK_BENCHMARK

    return [COACTION_VENUE_RISK_BENCHMARK]


def benchmark_catalog_as_json() -> list[dict[str, Any]]:
    records = []
    for spec in get_benchmark_catalog():
        record = asdict(spec)
        for key in list(record):
            if callable(record[key]):
                del record[key]
        records.append(record)
    return records


def resolve_benchmark(benchmark_id: str) -> BenchmarkSpec:
    for spec in get_benchmark_catalog():
        if spec.benchmark_id == benchmark_id:
            return spec
    raise ValueError(f"Unknown benchmark: {benchmark_id}")
