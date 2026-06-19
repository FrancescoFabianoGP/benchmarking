from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "submodules" / "zeus-service" / "app" / "workflow" / "local_db" / "coaction"
DEFAULT_CASE_PACK_PATH = ROOT / "cases" / "coaction_venue_risk" / "initial_case_pack.json"
DEFAULT_REPORT_DIR = ROOT / "reports" / "coaction_initial_draft"


@dataclass
class BenchmarkCase:
    case_id: str
    dataset: str
    query_type: str
    metric_key: str
    prompt: str
    gold_answer: list[str]
    evidence: dict[str, Any]
    metadata: dict[str, Any]


@dataclass
class Prediction:
    case_id: str
    runner: str
    answer: list[str]
    evidence: dict[str, Any]
    latency_ms: float


@dataclass
class CaseScore:
    case_id: str
    runner: str
    is_correct: bool
    expected: list[str]
    predicted: list[str]


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return float(stripped)


def _extract_county(court_name: str) -> str:
    if court_name == "All Courts":
        return court_name
    if "Supreme Court" in court_name:
        return court_name.replace(" Supreme Court", "")
    if "Superior Court" in court_name:
        return court_name.replace(" Superior Court", "")
    return court_name


def _normalize_answers(values: list[str]) -> list[str]:
    return sorted({value.strip() for value in values if value and value.strip()})


def _compare_answers(left: list[str], right: list[str]) -> bool:
    return _normalize_answers(left) == _normalize_answers(right)


def load_reference_data() -> dict[str, Any]:
    court_files = {
        "unicourt": DATA_ROOT / "unicourt_tables" / "Court Analysis Stats.csv",
        "coaction": DATA_ROOT / "coaction_tables" / "Court Analysis Stats.csv",
    }
    judge_files = {
        "unicourt": DATA_ROOT / "unicourt_tables" / "Judge MTD Rate.csv",
        "coaction": DATA_ROOT / "coaction_tables" / "Judge MTD Rate.csv",
    }
    cache_files = {
        "all_jurisdiction_summary": DATA_ROOT / "cache" / "all_jurisdiction_summary.json",
        "county_specific_summary": DATA_ROOT / "cache" / "county_specific_summary.json",
    }
    return {
        "court_rows": {name: _read_csv_rows(path) for name, path in court_files.items()},
        "judge_rows": {name: _read_csv_rows(path) for name, path in judge_files.items()},
        "cache": {name: _read_json(path) for name, path in cache_files.items()},
    }


def _personal_injury_overall_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    filtered = []
    for row in rows:
        if row["FILED_YEAR"] != "Overall":
            continue
        if row["areaOfLaw"] != "Personal Injury and Torts":
            continue
        county = _extract_county(row["COURT_NAME"])
        if county == "All Courts":
            continue
        copied = dict(row)
        copied["county"] = county
        filtered.append(copied)
    return filtered


def _overall_judge_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    filtered = []
    for row in rows:
        if row["FILED_YEAR"] != "Overall":
            continue
        copied = dict(row)
        copied["county"] = _extract_county(row["COURT_NAME"])
        if copied["county"] == "All Courts":
            continue
        filtered.append(copied)
    return filtered


def _top_counties_by_metric(
    rows: list[dict[str, str]],
    metric_key: str,
    want: str,
) -> tuple[list[str], float]:
    ranked = []
    for row in rows:
        metric_value = _to_float(row[metric_key])
        if metric_value is None or math.isnan(metric_value):
            continue
        ranked.append((row["county"], metric_value))
    if not ranked:
        return [], float("nan")
    comparator = min if want == "min" else max
    target_value = comparator(value for _, value in ranked)
    winners = [county for county, value in ranked if value == target_value]
    return _normalize_answers(winners), target_value


def _top_judges_for_county(
    rows: list[dict[str, str]],
    county: str,
) -> tuple[list[str], float]:
    ranked = []
    for row in rows:
        if row["county"] != county:
            continue
        rate = _to_float(row["DISMISSAL_RATE_PCT"])
        total_count = _to_float(row["MTD_TOTAL_COUNT"])
        if rate is None or total_count is None or total_count < 1:
            continue
        ranked.append((row["JUDGE_NAME"], rate))
    if not ranked:
        return [], float("nan")
    target_value = max(rate for _, rate in ranked)
    winners = [judge for judge, rate in ranked if rate == target_value]
    return _normalize_answers(winners), target_value


def build_initial_case_pack(reference_data: dict[str, Any]) -> list[BenchmarkCase]:
    metric_specs = [
        (
            "lowest_avg_case_duration",
            "AVG_CASE_DURATION",
            "min",
            "Which county has the lowest average case duration for Personal Injury and Torts?",
        ),
        (
            "lowest_avg_time_to_resolution",
            "AVG_TIME_TO_RESOLUTION",
            "min",
            "Which county has the lowest average time to resolution for Personal Injury and Torts?",
        ),
        (
            "highest_mtd_success_rate",
            "MTD_SUCCESS_RATE",
            "max",
            "Which county has the highest motion-to-dismiss success rate for Personal Injury and Torts?",
        ),
        (
            "highest_sj_success_rate",
            "SJ_SUCCESS_RATE",
            "max",
            "Which county has the highest summary-judgment success rate for Personal Injury and Torts?",
        ),
        (
            "lowest_avg_duration_no_trial",
            "AVG_DURATION_NO_TRIAL",
            "min",
            "Which county resolves no-trial Personal Injury and Torts cases the fastest on average?",
        ),
    ]
    case_pack: list[BenchmarkCase] = []
    case_number = 1

    for dataset, rows in reference_data["court_rows"].items():
        filtered_rows = _personal_injury_overall_rows(rows)
        for metric_slug, metric_key, want, question in metric_specs:
            winners, metric_value = _top_counties_by_metric(filtered_rows, metric_key, want)
            case_pack.append(
                BenchmarkCase(
                    case_id=f"case-{case_number:04d}",
                    dataset=dataset,
                    query_type="county_metric_extreme",
                    metric_key=metric_key,
                    prompt=f"{question} Use the {dataset} overall court stats table.",
                    gold_answer=winners,
                    evidence={
                        "source_table": f"{dataset}/Court Analysis Stats.csv",
                        "supporting_value": metric_value,
                    },
                    metadata={
                        "metric_slug": metric_slug,
                        "extreme": want,
                    },
                )
            )
            case_number += 1

    for dataset, rows in reference_data["judge_rows"].items():
        filtered_rows = _overall_judge_rows(rows)
        counties = sorted({row["county"] for row in filtered_rows})
        for county in counties:
            winners, metric_value = _top_judges_for_county(filtered_rows, county)
            case_pack.append(
                BenchmarkCase(
                    case_id=f"case-{case_number:04d}",
                    dataset=dataset,
                    query_type="county_top_judge_dismissal_rate",
                    metric_key="DISMISSAL_RATE_PCT",
                    prompt=(
                        f"For {county}, which judge has the highest dismissal rate "
                        f"in the {dataset} judge table overall rows?"
                    ),
                    gold_answer=winners,
                    evidence={
                        "source_table": f"{dataset}/Judge MTD Rate.csv",
                        "supporting_value": metric_value,
                        "county": county,
                    },
                    metadata={},
                )
            )
            case_number += 1

    return case_pack


def run_structured_lookup(
    case: BenchmarkCase,
    reference_data: dict[str, Any],
) -> Prediction:
    started = perf_counter()
    if case.query_type == "county_metric_extreme":
        rows = _personal_injury_overall_rows(reference_data["court_rows"][case.dataset])
        answer, metric_value = _top_counties_by_metric(
            rows,
            case.metric_key,
            case.metadata["extreme"],
        )
        evidence = {
            "source_table": f"{case.dataset}/Court Analysis Stats.csv",
            "supporting_value": metric_value,
        }
    elif case.query_type == "county_top_judge_dismissal_rate":
        rows = _overall_judge_rows(reference_data["judge_rows"][case.dataset])
        answer, metric_value = _top_judges_for_county(rows, case.evidence["county"])
        evidence = {
            "source_table": f"{case.dataset}/Judge MTD Rate.csv",
            "supporting_value": metric_value,
            "county": case.evidence["county"],
        }
    else:
        raise ValueError(f"Unsupported query type: {case.query_type}")
    latency_ms = (perf_counter() - started) * 1000
    return Prediction(
        case_id=case.case_id,
        runner="structured_lookup",
        answer=answer,
        evidence=evidence,
        latency_ms=latency_ms,
    )


def score_predictions(
    cases: list[BenchmarkCase],
    predictions: list[Prediction],
) -> tuple[list[CaseScore], dict[str, Any]]:
    case_by_id = {case.case_id: case for case in cases}
    scores = []
    for prediction in predictions:
        case = case_by_id[prediction.case_id]
        scores.append(
            CaseScore(
                case_id=case.case_id,
                runner=prediction.runner,
                is_correct=_compare_answers(case.gold_answer, prediction.answer),
                expected=case.gold_answer,
                predicted=prediction.answer,
            )
        )

    accuracy = mean(score.is_correct for score in scores) if scores else 0.0
    by_dataset = {}
    for dataset in sorted({case.dataset for case in cases}):
        dataset_scores = [
            score for score in scores if case_by_id[score.case_id].dataset == dataset
        ]
        by_dataset[dataset] = {
            "accuracy": mean(score.is_correct for score in dataset_scores)
            if dataset_scores
            else 0.0,
            "case_count": len(dataset_scores),
        }

    by_query_type = {}
    for query_type in sorted({case.query_type for case in cases}):
        query_scores = [
            score for score in scores if case_by_id[score.case_id].query_type == query_type
        ]
        by_query_type[query_type] = {
            "accuracy": mean(score.is_correct for score in query_scores)
            if query_scores
            else 0.0,
            "case_count": len(query_scores),
        }

    return scores, {
        "runner": predictions[0].runner if predictions else "unknown",
        "overall_accuracy": accuracy,
        "case_count": len(scores),
        "by_dataset": by_dataset,
        "by_query_type": by_query_type,
        "average_latency_ms": mean(pred.latency_ms for pred in predictions)
        if predictions
        else 0.0,
    }


def _json_ready_case(case: BenchmarkCase) -> dict[str, Any]:
    return asdict(case)


def _json_ready_prediction(prediction: Prediction) -> dict[str, Any]:
    return asdict(prediction)


def _json_ready_score(score: CaseScore) -> dict[str, Any]:
    return asdict(score)


def write_outputs(
    case_pack: list[BenchmarkCase],
    predictions: list[Prediction],
    scores: list[CaseScore],
    summary: dict[str, Any],
    case_pack_path: Path,
    report_dir: Path,
) -> None:
    case_pack_path.parent.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    with case_pack_path.open("w", encoding="utf-8") as handle:
        json.dump([_json_ready_case(case) for case in case_pack], handle, indent=2)

    with (report_dir / "predictions.json").open("w", encoding="utf-8") as handle:
        json.dump([_json_ready_prediction(pred) for pred in predictions], handle, indent=2)

    with (report_dir / "scores.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "summary": summary,
                "scores": [_json_ready_score(score) for score in scores],
            },
            handle,
            indent=2,
        )

    lines = [
        "# Coaction Initial Benchmark Draft",
        "",
        "This report is the first thin benchmark loop built from the existing local",
        "Coaction and UniCourt venue-risk tables already present in `submodules/zeus-service`.",
        "",
        "## Scorecard",
        "",
        f"- Runner: `{summary['runner']}`",
        f"- Cases: `{summary['case_count']}`",
        f"- Overall accuracy: `{summary['overall_accuracy']:.1%}`",
        f"- Average latency: `{summary['average_latency_ms']:.2f} ms`",
        "",
        "## Accuracy By Dataset",
        "",
        "| Dataset | Accuracy | Cases |",
        "|---|---:|---:|",
    ]
    for dataset, dataset_summary in summary["by_dataset"].items():
        lines.append(
            f"| {dataset} | {dataset_summary['accuracy']:.1%} | {dataset_summary['case_count']} |"
        )

    lines.extend(
        [
            "",
            "## Accuracy By Query Type",
            "",
            "| Query Type | Accuracy | Cases |",
            "|---|---:|---:|",
        ]
    )
    for query_type, query_summary in summary["by_query_type"].items():
        lines.append(
            f"| {query_type} | {query_summary['accuracy']:.1%} | {query_summary['case_count']} |"
        )

    lines.extend(
        [
            "",
            "## Case Results",
            "",
            "| Case | Dataset | Prompt | Expected | Predicted | Correct |",
            "|---|---|---|---|---|---|",
        ]
    )
    prediction_by_case = {prediction.case_id: prediction for prediction in predictions}
    score_by_case = {score.case_id: score for score in scores}
    for case in case_pack:
        prediction = prediction_by_case[case.case_id]
        score = score_by_case[case.case_id]
        lines.append(
            "| {case_id} | {dataset} | {prompt} | {expected} | {predicted} | {correct} |".format(
                case_id=case.case_id,
                dataset=case.dataset,
                prompt=case.prompt.replace("|", "/"),
                expected=", ".join(case.gold_answer),
                predicted=", ".join(prediction.answer),
                correct="yes" if score.is_correct else "no",
            )
        )

    with (report_dir / "scorecard.md").open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def run_initial_benchmark(
    case_pack_path: Path = DEFAULT_CASE_PACK_PATH,
    report_dir: Path = DEFAULT_REPORT_DIR,
) -> dict[str, Any]:
    reference_data = load_reference_data()
    case_pack = build_initial_case_pack(reference_data)
    predictions = [run_structured_lookup(case, reference_data) for case in case_pack]
    scores, summary = score_predictions(case_pack, predictions)
    write_outputs(case_pack, predictions, scores, summary, case_pack_path, report_dir)
    return {
        "case_pack_path": str(case_pack_path),
        "report_dir": str(report_dir),
        "summary": summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the initial benchmark draft on existing Coaction venue-risk data."
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
    args = parser.parse_args()
    result = run_initial_benchmark(
        case_pack_path=args.case_pack_path,
        report_dir=args.report_dir,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
