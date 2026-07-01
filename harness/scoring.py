from __future__ import annotations

from statistics import mean
from typing import Any

from harness.benchmark_types import BenchmarkCase, CaseScore, Prediction


def normalize_answers(values: list[str]) -> list[str]:
    return sorted({value.strip() for value in values if value and value.strip()})


def compare_answers(left: list[str], right: list[str]) -> bool:
    return normalize_answers(left) == normalize_answers(right)


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
                is_correct=compare_answers(case.gold_answer, prediction.answer),
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

    usage_totals = _aggregate_usage_metrics(predictions)

    return scores, {
        "runner": predictions[0].runner if predictions else "unknown",
        "overall_accuracy": accuracy,
        "case_count": len(scores),
        "by_dataset": by_dataset,
        "by_query_type": by_query_type,
        "average_latency_ms": mean(pred.latency_ms for pred in predictions)
        if predictions
        else 0.0,
        "average_wall_time_ms": mean(pred.wall_time_ms for pred in predictions)
        if predictions
        else 0.0,
        "average_cpu_time_ms": mean(pred.cpu_time_ms for pred in predictions)
        if predictions
        else 0.0,
        "average_io_wait_ms": mean(pred.io_wait_ms for pred in predictions)
        if predictions
        else 0.0,
        "total_wall_time_ms": sum(pred.wall_time_ms for pred in predictions),
        "total_cpu_time_ms": sum(pred.cpu_time_ms for pred in predictions),
        "total_io_wait_ms": sum(pred.io_wait_ms for pred in predictions),
        **usage_totals,
    }


def summarize_suite(
    cases: list[BenchmarkCase],
    predictions_by_baseline: dict[str, list[Prediction]],
) -> dict[str, Any]:
    suite = {}
    for baseline_id, predictions in predictions_by_baseline.items():
        _, summary = score_predictions(cases, predictions)
        suite[baseline_id] = summary
    return suite


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _aggregate_usage_metrics(predictions: list[Prediction]) -> dict[str, Any]:
    totals = {
        "cases_with_usage": 0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_tokens": 0,
        "total_estimated_cost_usd": 0.0,
        "cases_with_estimated_cost": 0,
    }
    for prediction in predictions:
        evidence = prediction.evidence if isinstance(prediction.evidence, dict) else {}
        usage = evidence.get("usage", {})
        if isinstance(usage, dict) and usage:
            totals["cases_with_usage"] += 1
            input_tokens = _as_int(usage.get("input_tokens")) or 0
            output_tokens = _as_int(usage.get("output_tokens")) or 0
            total_tokens = _as_int(usage.get("total_tokens"))
            totals["total_input_tokens"] += input_tokens
            totals["total_output_tokens"] += output_tokens
            totals["total_tokens"] += total_tokens if total_tokens is not None else input_tokens + output_tokens

        estimated_cost = _as_float(evidence.get("estimated_cost_usd"))
        if estimated_cost is not None:
            totals["cases_with_estimated_cost"] += 1
            totals["total_estimated_cost_usd"] += estimated_cost

    if totals["cases_with_usage"] == 0:
        totals["total_input_tokens"] = None
        totals["total_output_tokens"] = None
        totals["total_tokens"] = None
    if totals["cases_with_estimated_cost"] == 0:
        totals["total_estimated_cost_usd"] = None
        totals["average_estimated_cost_per_case_usd"] = None
    else:
        totals["average_estimated_cost_per_case_usd"] = (
            totals["total_estimated_cost_usd"] / totals["cases_with_estimated_cost"]
        )
    return totals
