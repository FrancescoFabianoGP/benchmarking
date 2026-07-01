from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path
from time import perf_counter
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.benchmark_types import BenchmarkCase
from harness.framework_runners.common import read_case_from_stdin

from app.workflow.workflow_pipeline_registry.coaction_workflows.pipeline_venue_risk_litigation_trend_workflow import (
    VenueRiskLitigationTrendWorkflowPipeline,
)
from growth_protocol_ai_sdk.workflow.workflow_config import WorkflowConfig
from growth_protocol_ai_sdk.workflow.workflow_execution_manager import (
    InMemoryWorkflowExecutionManager,
    set_execution_manager,
)
from growth_protocol_ai_sdk.workflow.workflow_registry import WorkflowRegistry


METRIC_ATTRIBUTE_BY_KEY = {
    "AVG_CASE_DURATION": "avg_case_duration",
    "AVG_TIME_TO_RESOLUTION": "avg_time_to_resolution",
    "MTD_SUCCESS_RATE": "mtd_success_rate",
    "SJ_SUCCESS_RATE": "sj_success_rate",
    "AVG_DURATION_NO_TRIAL": "avg_duration_no_trial",
}
SECTION_HEADERS = {
    "unicourt": "UniCourt Analysis",
    "coaction": "Coaction Cases Analysis",
}
JUDGE_TABLE_NAME = "Highest Judge Dismissal Rates for Personal Injury"
ZEUS_SERVICE_ROOT = ROOT / "GP_components" / "zeus-service"
_REGISTRY_INITIALIZED = False


def _normalize_county_name(value: object) -> str | None:
    if value is None:
        return None
    if hasattr(value, "value"):
        return str(getattr(value, "value"))
    return str(value)


def _initialize_zeus_registry() -> None:
    global _REGISTRY_INITIALIZED
    if _REGISTRY_INITIALIZED:
        return

    workflows_module_path = ZEUS_SERVICE_ROOT / "app" / "workflow"
    WorkflowRegistry.set_default_workflow_yaml_directory(
        str(workflows_module_path / "workflows_registry")
    )
    WorkflowRegistry.add_atomic_actions_directory(str(workflows_module_path / "core_engine"))
    WorkflowRegistry.add_atomic_actions_directory(str(workflows_module_path / "atomic_actions"))
    set_execution_manager(InMemoryWorkflowExecutionManager())
    _REGISTRY_INITIALIZED = True


def _pick_dataset_rows(result: object, dataset: str) -> list[object]:
    insights = getattr(result, "insights")
    if dataset == "unicourt":
        rows = getattr(insights, "unicourt_court_stats_raw", None)
    elif dataset == "coaction":
        rows = getattr(insights, "coaction_court_stats_raw", None)
    else:
        raise ValueError(f"Unsupported Zeus dataset: {dataset}")
    return list(rows or [])


def _extract_metric_answer(case: BenchmarkCase, result: object) -> tuple[list[str], dict[str, object]]:
    metric_attribute = METRIC_ATTRIBUTE_BY_KEY.get(case.metric_key)
    if metric_attribute is None:
        raise ValueError(f"Unsupported metric key for Zeus extraction: {case.metric_key}")

    ranked: list[tuple[str, float]] = []
    for row in _pick_dataset_rows(result, case.dataset):
        if getattr(row, "filed_year", None) != "Overall":
            continue
        if getattr(row, "area_of_law", None) != "Personal Injury and Torts":
            continue
        county_name = _normalize_county_name(getattr(row, "county", None))
        metric_value = getattr(row, metric_attribute, None)
        if county_name is None or metric_value is None:
            continue
        ranked.append((county_name, float(metric_value)))

    if not ranked:
        raise RuntimeError(
            f"Zeus did not return usable overall rows for dataset={case.dataset} metric={case.metric_key}."
        )

    comparator = min if case.metadata.get("extreme") == "min" else max
    target_value = comparator(value for _, value in ranked)
    winners = sorted({county for county, value in ranked if value == target_value})
    return winners, {
        "dataset": case.dataset,
        "metric_key": case.metric_key,
        "supporting_value": target_value,
        "source": "zeus_workflow.insights.*_court_stats_raw",
        "ranked_rows": ranked,
    }


def _extract_dataset_section(summary: str, dataset: str) -> str:
    header = SECTION_HEADERS[dataset]
    pattern = rf"### {re.escape(header)}.*?(?=\n### |\Z)"
    match = re.search(pattern, summary, flags=re.DOTALL)
    return match.group(0) if match else ""


def _table_matches_dataset(table: object, dataset: str) -> bool:
    is_coaction = bool(getattr(table, "coaction_table", False))
    return is_coaction if dataset == "coaction" else not is_coaction


def _extract_judge_answer_from_structured_tables(
    case: BenchmarkCase,
    result: object,
) -> tuple[list[str], dict[str, object]] | None:
    insights = getattr(result, "insights")
    by_county = getattr(insights, "county_specific_jurisdiction_analysis", None) or {}
    target_tables = None
    for county_key, tables in by_county.items():
        if _normalize_county_name(county_key) == case.evidence["county"]:
            target_tables = list(tables or [])
            break

    if not target_tables:
        return None

    judge_table = next(
        (
            table
            for table in target_tables
            if getattr(table, "name", "") == JUDGE_TABLE_NAME
            and _table_matches_dataset(table, case.dataset)
        ),
        None,
    )
    if judge_table is None:
        return None

    rows = list(getattr(judge_table, "rows", []) or [])
    if len(rows) < 2:
        return None

    header = [str(item) for item in rows[0]]
    try:
        judge_index = header.index("Judge")
        rate_index = header.index("Dismissal Rate (%)")
    except ValueError:
        return None

    ranked: list[tuple[str, float]] = []
    for row in rows[1:]:
        if len(row) <= max(judge_index, rate_index):
            continue
        judge_name = str(row[judge_index]).strip()
        rate_raw = str(row[rate_index]).strip()
        if not judge_name or not rate_raw or rate_raw == "None":
            continue
        try:
            rate_value = float(rate_raw)
        except ValueError:
            continue
        ranked.append((judge_name, rate_value))

    if not ranked:
        return None

    target_value = max(rate for _, rate in ranked)
    winners = sorted({judge for judge, rate in ranked if rate == target_value})
    return winners, {
        "dataset": case.dataset,
        "county": case.evidence["county"],
        "source": "zeus_workflow.insights.county_specific_jurisdiction_analysis",
        "table_name": JUDGE_TABLE_NAME,
        "supporting_value": target_value,
        "ranked_rows": ranked,
    }


def _extract_judge_answer(case: BenchmarkCase, result: object) -> tuple[list[str], dict[str, object]]:
    structured = _extract_judge_answer_from_structured_tables(case, result)
    if structured is not None:
        return structured

    insights = getattr(result, "insights")
    by_county = getattr(insights, "insight_summary_specific_jurisdiction", None) or {}
    county_summary = ""
    for county_key, summary in by_county.items():
        if _normalize_county_name(county_key) == case.evidence["county"]:
            county_summary = str(summary)
            break

    if not county_summary:
        raise RuntimeError(
            f"Zeus did not return a county-specific summary for {case.evidence['county']}."
        )

    dataset_section = _extract_dataset_section(county_summary, case.dataset)
    if not dataset_section:
        raise RuntimeError(
            f"Zeus county-specific summary for {case.evidence['county']} did not include a {case.dataset} section."
        )

    match = re.search(
        r"- Judge (.+?) has the highest dismissal rate",
        dataset_section,
    )
    if not match:
        raise RuntimeError(
            f"Zeus summary for {case.evidence['county']} did not expose a judge dismissal-rate answer."
        )

    judge_name = match.group(1).strip()
    return [judge_name], {
        "dataset": case.dataset,
        "county": case.evidence["county"],
        "source": "zeus_workflow.insights.insight_summary_specific_jurisdiction",
        "summary_excerpt": dataset_section,
    }


async def run_zeus_case(case: BenchmarkCase) -> dict[str, object]:
    _initialize_zeus_registry()
    config = WorkflowConfig(
        thread_id=f"benchmark-{case.case_id}",
        run_id=uuid4(),
        user_id="benchmark-harness",
    )
    started = perf_counter()
    pipeline = VenueRiskLitigationTrendWorkflowPipeline(
        config=config,
        jurisdiction="Los Angeles County, Bronx County, Kings County",
    )
    result = await pipeline.orchestrate()
    latency_ms = (perf_counter() - started) * 1000

    if case.query_type == "county_metric_extreme":
        answer, extraction_evidence = _extract_metric_answer(case, result)
    elif case.query_type == "county_top_judge_dismissal_rate":
        answer, extraction_evidence = _extract_judge_answer(case, result)
    else:
        raise ValueError(f"Unsupported Zeus benchmark query type: {case.query_type}")

    structured_output = result.to_structured_output()
    return {
        "answer": answer,
        "evidence": {
            "framework": "zeus",
            "variant": "venue_risk_workflow_live",
            "workflow": "VenueRiskLitigationTrendWorkflowPipeline",
            "jurisdiction": str(getattr(result, "jurisdiction", "")),
            "strategic_summary": getattr(
                getattr(result, "insights"),
                "strategic_summary_across_all_jurisdictions",
                None,
            ),
            "structured_output_count": len(structured_output[2]),
            "extraction": extraction_evidence,
        },
        "latency_ms": latency_ms,
    }


def main() -> None:
    case = read_case_from_stdin()
    json.dump(asyncio.run(run_zeus_case(case)), fp=sys.stdout)


if __name__ == "__main__":
    main()
