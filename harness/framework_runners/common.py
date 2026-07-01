from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from dataclasses import asdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.benchmark_types import BenchmarkCase  # noqa: E402
from harness.benchmarks.coaction_venue_risk import (  # noqa: E402
    DATA_ROOT,
    load_reference_data,
    overall_judge_rows,
    personal_injury_overall_rows,
    top_counties_by_metric,
    top_judges_for_county,
)


DEFAULT_FRAMEWORK_MODEL = "gpt-4o-mini"
DEFAULT_HTTP_USER_AGENT = "OpenAI/Python 1.0.0"


def read_case_from_stdin() -> BenchmarkCase:
    payload = json.load(sys.stdin)
    return BenchmarkCase(**payload["case"])


def case_as_payload(case: BenchmarkCase) -> dict[str, Any]:
    return asdict(case)


def lookup_answer(case: BenchmarkCase) -> tuple[list[str], dict[str, Any]]:
    reference_data = load_reference_data()
    if case.query_type == "county_metric_extreme":
        rows = personal_injury_overall_rows(reference_data["court_rows"][case.dataset])
        answer, metric_value = top_counties_by_metric(
            rows,
            case.metric_key,
            case.metadata["extreme"],
        )
        return answer, {
            "source_table": f"{case.dataset}/Court Analysis Stats.csv",
            "supporting_value": metric_value,
        }
    if case.query_type == "county_top_judge_dismissal_rate":
        rows = overall_judge_rows(reference_data["judge_rows"][case.dataset])
        answer, metric_value = top_judges_for_county(rows, case.evidence["county"])
        return answer, {
            "source_table": f"{case.dataset}/Judge MTD Rate.csv",
            "supporting_value": metric_value,
            "county": case.evidence["county"],
        }
    raise ValueError(f"Unsupported query type: {case.query_type}")


def parse_answer_text(text: str) -> list[str]:
    candidates = [text.strip()]
    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, flags=re.DOTALL)
    if fenced_match:
        candidates.insert(0, fenced_match.group(1).strip())
    object_match = re.search(r"(\{.*\})", text, flags=re.DOTALL)
    if object_match:
        candidates.append(object_match.group(1).strip())

    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("answer"), list):
            return [str(item) for item in payload["answer"]]
        if isinstance(payload, list):
            return [str(item) for item in payload]
    stripped = text.strip()
    return [stripped] if stripped else []


def serialize_message(message: Any) -> dict[str, Any]:
    content = getattr(message, "content", None)
    if isinstance(content, list):
        serialized_content = [str(item) for item in content]
    else:
        serialized_content = content if isinstance(content, str) else str(content)
    return {
        "type": type(message).__name__,
        "source": getattr(message, "source", getattr(message, "sent_from", "")),
        "content": serialized_content,
    }


def require_openai_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Live framework baselines require OPENAI_API_KEY. "
            "Set it before running the benchmark suite."
        )
    return api_key


def openai_base_url() -> str:
    configured = os.getenv("OPENAI_BASE_URL")
    if configured:
        return configured.rstrip("/")
    return "https://api.openai.com/v1"


def openai_chat_completions_url() -> str:
    configured = os.getenv("OPENAI_BASE_URL")
    if configured:
        return f"{configured.rstrip('/')}/chat/completions"
    return "https://api.openai.com/v1/chat/completions"


def framework_model_name(*env_names: str) -> str:
    for env_name in env_names:
        value = os.getenv(env_name)
        if value:
            return value
    return os.getenv("BENCHMARK_FRAMEWORK_MODEL", os.getenv("OPENAI_MODEL", DEFAULT_FRAMEWORK_MODEL))


def openai_text_completion(*, prompt: str, model: str, system_prompt: str) -> tuple[str, dict[str, Any]]:
    request = urllib.request.Request(
        openai_chat_completions_url(),
        data=json.dumps(
            {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
            }
        ).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {require_openai_api_key()}",
            "Content-Type": "application/json",
            "User-Agent": DEFAULT_HTTP_USER_AGENT,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = json.load(response)
    choices = payload.get("choices", [])
    if choices:
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, str):
            return content, payload
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(str(item.get("text", "")))
                else:
                    text_parts.append(str(item))
            return "\n".join(part for part in text_parts if part), payload
    return "", payload


def openai_usage(payload: dict[str, Any]) -> dict[str, Any]:
    usage = payload.get("usage", {})
    if not isinstance(usage, dict):
        return {}
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    total_tokens = usage.get("total_tokens")
    return {
        "input_tokens": int(prompt_tokens) if isinstance(prompt_tokens, (int, float)) else None,
        "output_tokens": int(completion_tokens) if isinstance(completion_tokens, (int, float)) else None,
        "total_tokens": int(total_tokens) if isinstance(total_tokens, (int, float)) else None,
        "raw_usage": usage,
    }


def estimate_openai_cost_usd(model: str, usage: dict[str, Any]) -> float | None:
    input_price_raw = os.getenv("OPENAI_INPUT_COST_PER_1M")
    output_price_raw = os.getenv("OPENAI_OUTPUT_COST_PER_1M")
    defaults = {
        "gpt-4o-mini": (0.15, 0.60),
    }
    try:
        input_price = float(input_price_raw) if input_price_raw else None
        output_price = float(output_price_raw) if output_price_raw else None
    except ValueError:
        input_price = None
        output_price = None
    if input_price is None or output_price is None:
        if model not in defaults:
            return None
        input_price, output_price = defaults[model]
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
        return None
    return (input_tokens / 1_000_000.0) * input_price + (output_tokens / 1_000_000.0) * output_price


def _court_stats_path(dataset: str) -> Path:
    return DATA_ROOT / f"{dataset}_tables" / "Court Analysis Stats.csv"


def _judge_stats_path(dataset: str) -> Path:
    return DATA_ROOT / f"{dataset}_tables" / "Judge MTD Rate.csv"


def _summary_paths() -> dict[str, Path]:
    return {
        "all_jurisdiction_summary": DATA_ROOT / "cache" / "all_jurisdiction_summary.json",
        "county_specific_summary": DATA_ROOT / "cache" / "county_specific_summary.json",
    }


def case_prompt_bundle(case: BenchmarkCase) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "dataset": case.dataset,
        "query_type": case.query_type,
        "metric_key": case.metric_key,
        "prompt": case.prompt,
        "required_output": {"answer": ["exact county or judge names"]},
        "allowed_sources": list_case_files(case),
    }


def list_case_files(case: BenchmarkCase) -> list[str]:
    files = [
        str(_court_stats_path(case.dataset).relative_to(ROOT)),
        str(_judge_stats_path(case.dataset).relative_to(ROOT)),
    ]
    files.extend(str(path.relative_to(ROOT)) for path in _summary_paths().values())
    return files


def read_relevant_court_stats(case: BenchmarkCase) -> dict[str, Any]:
    reference_data = load_reference_data()
    rows = personal_injury_overall_rows(reference_data["court_rows"][case.dataset])
    return {
        "source_table": f"{case.dataset}/Court Analysis Stats.csv",
        "question_focus": case.metric_key,
        "rows": [
            {
                "county": row["county"],
                "AVG_CASE_DURATION": row["AVG_CASE_DURATION"],
                "AVG_TIME_TO_RESOLUTION": row["AVG_TIME_TO_RESOLUTION"],
                "AVG_DURATION_NO_TRIAL": row["AVG_DURATION_NO_TRIAL"],
                "MTD_SUCCESS_RATE": row["MTD_SUCCESS_RATE"],
                "SJ_SUCCESS_RATE": row["SJ_SUCCESS_RATE"],
            }
            for row in rows
        ],
    }


def read_relevant_judge_stats(case: BenchmarkCase) -> dict[str, Any]:
    reference_data = load_reference_data()
    rows = overall_judge_rows(reference_data["judge_rows"][case.dataset])
    county = case.evidence.get("county")
    if county:
        rows = [row for row in rows if row["county"] == county]
    return {
        "source_table": f"{case.dataset}/Judge MTD Rate.csv",
        "county": county,
        "rows": [
            {
                "judge_name": row["JUDGE_NAME"],
                "county": row["county"],
                "DISMISSAL_RATE_PCT": row["DISMISSAL_RATE_PCT"],
                "MTD_TOTAL_COUNT": row["MTD_TOTAL_COUNT"],
            }
            for row in rows
        ],
    }


def read_relevant_summaries(case: BenchmarkCase) -> dict[str, Any]:
    reference_data = load_reference_data()
    cache = reference_data["cache"]
    county = case.evidence.get("county")
    return {
        "all_jurisdiction_summary": cache["all_jurisdiction_summary"].get(f"{case.dataset}_analysis", ""),
        "county_specific_summary": cache["county_specific_summary"].get(county, "") if county else "",
    }


def case_materials(case: BenchmarkCase) -> dict[str, Any]:
    materials = {
        "case": case_prompt_bundle(case),
        "court_stats": read_relevant_court_stats(case),
        "judge_stats": read_relevant_judge_stats(case),
        "summaries": read_relevant_summaries(case),
    }
    return materials


def list_available_sources_tool(case: BenchmarkCase) -> dict[str, Any]:
    return {
        "files": list_case_files(case),
        "recommended_first_source": case.evidence.get("source_table"),
    }


def tool_instructions(case: BenchmarkCase) -> str:
    return "\n".join(
        [
            "You are answering a benchmark case over local venue-risk data.",
            'Return only JSON with the shape {"answer": ["..."]}.',
            "Use exact county or judge names from the data you inspect.",
            "Do not fabricate values or source files.",
            f"Dataset: {case.dataset}",
            f"Question: {case.prompt}",
            f"Primary source hint: {case.evidence.get('source_table', '')}",
        ]
    )


def serialized_case_materials(case: BenchmarkCase) -> str:
    return json.dumps(case_materials(case), indent=2, sort_keys=True)
