from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any

from harness.benchmark_types import BenchmarkCase, Prediction

DEFAULT_OPENAI_HTTP_USER_AGENT = "OpenAI/Python 1.0.0"
DEFAULT_ANTHROPIC_HTTP_USER_AGENT = "Anthropic/Python 0.0.0"
OPENAI_DEFAULT_PRICING_PER_1M: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
}
ANTHROPIC_DEFAULT_PRICING_PER_1M: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-6": (3.0, 15.0),
}


@dataclass(frozen=True)
class BaselineSpec:
    baseline_id: str
    label: str
    category: str
    runner_kind: str
    provider: str | None
    model_env_var: str | None
    default_model: str | None
    spreadsheet_basis: str
    description: str
    implementation_status: str
    required_env_vars: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def build_prompt(case: BenchmarkCase) -> str:
    return "\n".join(
        [
            "You are answering a benchmark case.",
            'Return only JSON with the shape {"answer": ["..."]}.',
            "Use exact county or judge names from the provided question.",
            "If more than one answer ties, return all answers as strings.",
            "",
            f"Dataset: {case.dataset}",
            f"Question: {case.prompt}",
        ]
    )


def build_contextual_prompt(case: BenchmarkCase) -> str:
    from harness.framework_runners.common import list_case_files, serialized_case_materials

    return "\n\n".join(
        [
            "You are answering a benchmark case over local venue-risk benchmark materials.",
            'Return only JSON with the shape {"answer": ["..."]}.',
            "Use exact county or judge names from the provided materials.",
            "If more than one answer ties, return all answers as strings.",
            "",
            f"Dataset: {case.dataset}",
            f"Question: {case.prompt}",
            "Source files available for this case:",
            json.dumps(list_case_files(case), indent=2),
            "Relevant benchmark materials:",
            serialized_case_materials(case),
        ]
    )


def get_baseline_catalog() -> list[BaselineSpec]:
    return [
        BaselineSpec(
            baseline_id="structured_lookup",
            label="Structured Lookup",
            category="deterministic_reference",
            runner_kind="structured_lookup",
            provider=None,
            model_env_var=None,
            default_model=None,
            spreadsheet_basis="Internal reference baseline",
            description="Reads the local benchmark tables directly and returns exact answers.",
            implementation_status="ready",
            notes=[
                "Ground-truth sanity check for the thin draft.",
                "Useful as a regression guard while richer baselines are added.",
            ],
        ),
        BaselineSpec(
            baseline_id="openai_raw_llm",
            label="OpenAI Raw LLM",
            category="llm_only",
            runner_kind="openai_raw_llm",
            provider="openai",
            model_env_var="OPENAI_MODEL",
            default_model="gpt-5",
            spreadsheet_basis="Approach / baseline: LLM-only analyst",
            description="Prompt-only GPT baseline over the same case question and output schema.",
            implementation_status="offline_ready_live_if_configured",
            required_env_vars=["OPENAI_API_KEY"],
            notes=[
                "Set OPENAI_API_KEY and optionally OPENAI_MODEL before running.",
                "No tools or retrieval beyond the benchmark prompt.",
            ],
        ),
        BaselineSpec(
            baseline_id="openai_with_context",
            label="OpenAI With Context",
            category="llm_with_context",
            runner_kind="openai_with_context",
            provider="openai",
            model_env_var="OPENAI_MODEL",
            default_model="gpt-5",
            spreadsheet_basis="Approach / baseline: LLM analyst with relevant benchmark tables in context",
            description="OpenAI baseline with the relevant local benchmark table rows and summaries included in the request.",
            implementation_status="live_if_configured",
            required_env_vars=["OPENAI_API_KEY"],
            notes=[
                "Sends the case question plus the relevant local benchmark materials in the prompt.",
                "Uses the same Cloudflare OpenAI gateway path as the raw baseline when OPENAI_BASE_URL is set.",
            ],
        ),
        BaselineSpec(
            baseline_id="anthropic_raw_llm",
            label="Anthropic Raw LLM",
            category="llm_only",
            runner_kind="anthropic_raw_llm",
            provider="anthropic",
            model_env_var="ANTHROPIC_MODEL",
            default_model="claude-sonnet-4-6",
            spreadsheet_basis="Approach / baseline: LLM-only analyst",
            description="Prompt-only Claude baseline over the same case question and output schema.",
            implementation_status="offline_ready_live_if_configured",
            required_env_vars=["ANTHROPIC_API_KEY"],
            notes=[
                "Set ANTHROPIC_API_KEY and optionally ANTHROPIC_MODEL before running.",
                "No tools or retrieval beyond the benchmark prompt.",
            ],
        ),
        BaselineSpec(
            baseline_id="anthropic_with_context",
            label="Anthropic With Context",
            category="llm_with_context",
            runner_kind="anthropic_with_context",
            provider="anthropic",
            model_env_var="ANTHROPIC_MODEL",
            default_model="claude-sonnet-4-6",
            spreadsheet_basis="Approach / baseline: Claude analyst with relevant benchmark tables in context",
            description="Anthropic baseline with the relevant local benchmark table rows and summaries included in the request.",
            implementation_status="live_if_configured",
            required_env_vars=["ANTHROPIC_API_KEY"],
            notes=[
                "Sends the case question plus the relevant local benchmark materials in the prompt.",
                "Uses the configured ANTHROPIC_BASE_URL when present.",
            ],
        ),
        BaselineSpec(
            baseline_id="react_agent",
            label="ReAct Agent",
            category="open_tooling",
            runner_kind="react_agent",
            provider=None,
            model_env_var=None,
            default_model=None,
            spreadsheet_basis="Approach / baseline: ReAct agent; Paper to read: ReAct",
            description="Open agent baseline with thought-action-observation loops and tool calls.",
            implementation_status="framework_wrapper_requires_runtime",
            required_env_vars=["OPENAI_API_KEY"],
            notes=[
                "Good open baseline for agentic tool-use.",
                "Runs through a live AutoGen assistant-agent wrapper once `python3 scripts/install_baseline_runtimes.py --all` has been run.",
            ],
        ),
        BaselineSpec(
            baseline_id="multi_agent_analyst_coder_critic",
            label="Multi-Agent Analyst/Coder/Critic",
            category="open_tooling",
            runner_kind="multi_agent_analyst_coder_critic",
            provider=None,
            model_env_var=None,
            default_model=None,
            spreadsheet_basis="Approach / baseline: Multi-agent analyst/coder/critic workflow; Paper to read: AutoGen",
            description="Specialized multi-agent workflow baseline for analysis and self-critique.",
            implementation_status="framework_wrapper_requires_runtime",
            required_env_vars=["OPENAI_API_KEY"],
            notes=[
                "Good comparator for orchestration-heavy open tooling.",
                "Runs through a live MetaGPT multi-role wrapper once `python3 scripts/install_baseline_runtimes.py --all` has been run.",
            ],
        ),
        BaselineSpec(
            baseline_id="autogen_multi_agent",
            label="AutoGen Multi-Agent",
            category="agentic_architecture",
            runner_kind="autogen_multi_agent",
            provider=None,
            model_env_var=None,
            default_model=None,
            spreadsheet_basis="Paper to read: AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation",
            description="Conversational multi-agent architecture baseline for collaborative data-analysis workflows.",
            implementation_status="framework_wrapper_requires_runtime",
            required_env_vars=["OPENAI_API_KEY"],
            notes=[
                "Strong agentic architecture comparator for orchestration-heavy tasks.",
                "Runs through a live AutoGen group-chat wrapper once `python3 scripts/install_baseline_runtimes.py --all` has been run.",
            ],
        ),
        BaselineSpec(
            baseline_id="metagpt_sop_agent",
            label="MetaGPT SOP Agent",
            category="agentic_architecture",
            runner_kind="metagpt_sop_agent",
            provider=None,
            model_env_var=None,
            default_model=None,
            spreadsheet_basis="Paper to read: MetaGPT: Meta Programming for a Multi-Agent Collaborative Framework",
            description="Multi-agent SOP-style architecture baseline emphasizing role separation and staged execution.",
            implementation_status="framework_wrapper_requires_runtime",
            required_env_vars=["OPENAI_API_KEY"],
            notes=[
                "Interesting comparator if we want to benchmark GP as an orchestrator.",
                "Runs through a live MetaGPT Data Interpreter wrapper once `python3 scripts/install_baseline_runtimes.py --all` has been run.",
            ],
        ),
        BaselineSpec(
            baseline_id="single_agent_data_analyst",
            label="Single-Agent Data Analyst",
            category="agentic_architecture",
            runner_kind="single_agent_data_analyst",
            provider=None,
            model_env_var=None,
            default_model=None,
            spreadsheet_basis="Benchmarks: DABStep / InfiAgent-DABench / FDABench",
            description="Single open data agent baseline over heterogeneous files and analytical questions.",
            implementation_status="framework_wrapper_requires_runtime",
            required_env_vars=["OPENAI_API_KEY"],
            notes=[
                "Runs through a live LangGraph wrapper once `python3 scripts/install_baseline_runtimes.py --all` has been run.",
                "Natural bridge between raw LLM baselines and multi-agent orchestration baselines.",
            ],
        ),
        BaselineSpec(
            baseline_id="gp_zeus_venue_risk",
            label="GP Zeus Venue Risk",
            category="internal_gp_system",
            runner_kind="gp_zeus_venue_risk",
            provider=None,
            model_env_var=None,
            default_model=None,
            spreadsheet_basis="GP workflow baseline: Zeus venue-risk litigation trend workflow",
            description="Runs the real Zeus venue-risk workflow and extracts benchmark answers from its structured output.",
            implementation_status="framework_wrapper_requires_runtime_and_zeus_llm_config",
            required_env_vars=[],
            notes=[
                "Install the repo-local Zeus runtime with `python3 scripts/install_baseline_runtimes.py --baseline gp_zeus_venue_risk`.",
                "This baseline uses the in-repo `GP_components/zeus-service` workflow rather than a simplified wrapper architecture.",
                "The harness auto-configures a local workflow cache and maps OPENAI-style Cloudflare gateway settings into the Zeus Cloudflare ZDR env vars.",
                "For this Coaction benchmark path, the main live dependency is LLM access plus the repo-local Zeus runtime.",
            ],
        ),
    ]


def baseline_catalog_as_json() -> list[dict[str, Any]]:
    return [asdict(spec) for spec in get_baseline_catalog()]


def resolve_baseline(baseline_id: str) -> BaselineSpec:
    for spec in get_baseline_catalog():
        if spec.baseline_id == baseline_id:
            return spec
    raise ValueError(f"Unknown baseline: {baseline_id}")


def configured_model_name(spec: BaselineSpec) -> str | None:
    if not spec.model_env_var:
        return spec.default_model
    return os.getenv(spec.model_env_var, spec.default_model)


def missing_env_vars(spec: BaselineSpec) -> list[str]:
    if spec.baseline_id == "gp_zeus_venue_risk":
        missing: list[str] = []
        if not (
            os.getenv("OPENAI_API_KEY") or os.getenv("CLOUDFLARE_ZDR_AI_GATEWAY_API_KEY")
        ):
            missing.append("OPENAI_API_KEY or CLOUDFLARE_ZDR_AI_GATEWAY_API_KEY")
        if not (
            os.getenv("OPENAI_BASE_URL")
            or os.getenv("ANTHROPIC_BASE_URL")
            or os.getenv("CLOUDFLARE_ZDR_AI_GATEWAY_BASE_URL")
        ):
            missing.append(
                "OPENAI_BASE_URL or ANTHROPIC_BASE_URL or CLOUDFLARE_ZDR_AI_GATEWAY_BASE_URL"
            )
        return missing
    return [name for name in spec.required_env_vars if not os.getenv(name)]


def _openai_chat_completions_url() -> str:
    configured = os.getenv("OPENAI_BASE_URL")
    if configured:
        return f"{configured.rstrip('/')}/chat/completions"
    return "https://api.openai.com/v1/chat/completions"


def _anthropic_messages_url() -> str:
    base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
    if base_url.endswith("/v1"):
        return f"{base_url}/messages"
    return f"{base_url}/v1/messages"


def _anthropic_gateway_api_key() -> str:
    return os.getenv("ANTHROPIC_GATEWAY_API_KEY", os.environ["ANTHROPIC_API_KEY"])


def _anthropic_headers() -> dict[str, str]:
    gateway_api_key = _anthropic_gateway_api_key()
    return {
        "x-api-key": gateway_api_key,
        "anthropic-version": os.getenv("ANTHROPIC_VERSION", "2023-06-01"),
        "content-type": "application/json",
        "User-Agent": DEFAULT_ANTHROPIC_HTTP_USER_AGENT,
        "cf-aig-authorization": f"Bearer {gateway_api_key}",
    }


def _extract_json_answer(text: str) -> list[str]:
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


def _openai_usage(payload: dict[str, Any]) -> dict[str, Any]:
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


def _anthropic_usage(payload: dict[str, Any]) -> dict[str, Any]:
    usage = payload.get("usage", {})
    if not isinstance(usage, dict):
        return {}
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    cache_creation_input_tokens = usage.get("cache_creation_input_tokens")
    cache_read_input_tokens = usage.get("cache_read_input_tokens")
    total_tokens = None
    if isinstance(input_tokens, (int, float)) or isinstance(output_tokens, (int, float)):
        total_tokens = int(input_tokens or 0) + int(output_tokens or 0)
    return {
        "input_tokens": int(input_tokens) if isinstance(input_tokens, (int, float)) else None,
        "output_tokens": int(output_tokens) if isinstance(output_tokens, (int, float)) else None,
        "cache_creation_input_tokens": int(cache_creation_input_tokens)
        if isinstance(cache_creation_input_tokens, (int, float))
        else None,
        "cache_read_input_tokens": int(cache_read_input_tokens)
        if isinstance(cache_read_input_tokens, (int, float))
        else None,
        "total_tokens": total_tokens,
        "raw_usage": usage,
    }


def _configured_price(env_name: str) -> float | None:
    raw_value = os.getenv(env_name)
    if not raw_value:
        return None
    try:
        return float(raw_value)
    except ValueError:
        return None


def _estimate_openai_cost_usd(model: str, usage: dict[str, Any]) -> float | None:
    input_price = _configured_price("OPENAI_INPUT_COST_PER_1M")
    output_price = _configured_price("OPENAI_OUTPUT_COST_PER_1M")
    if input_price is None or output_price is None:
        defaults = OPENAI_DEFAULT_PRICING_PER_1M.get(model)
        if defaults is None:
            return None
        input_price, output_price = defaults
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
        return None
    return (input_tokens / 1_000_000.0) * input_price + (output_tokens / 1_000_000.0) * output_price


def _estimate_anthropic_cost_usd(model: str, usage: dict[str, Any]) -> float | None:
    input_price = _configured_price("ANTHROPIC_INPUT_COST_PER_1M")
    output_price = _configured_price("ANTHROPIC_OUTPUT_COST_PER_1M")
    if input_price is None or output_price is None:
        defaults = ANTHROPIC_DEFAULT_PRICING_PER_1M.get(model)
        if defaults is None:
            return None
        input_price, output_price = defaults
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
        return None
    return (input_tokens / 1_000_000.0) * input_price + (output_tokens / 1_000_000.0) * output_price


def run_openai_raw_llm(case: BenchmarkCase, model: str) -> Prediction:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": build_prompt(case)}],
    }
    request = urllib.request.Request(
        _openai_chat_completions_url(),
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": "application/json",
            "User-Agent": DEFAULT_OPENAI_HTTP_USER_AGENT,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    choices = payload.get("choices", [])
    text = ""
    if choices:
        text = str(choices[0].get("message", {}).get("content", ""))
    answer = _extract_json_answer(text)
    usage = _openai_usage(payload)
    return Prediction(
        case_id=case.case_id,
        runner="openai_raw_llm",
        answer=answer,
        evidence={
            "model": model,
            "raw_response": text,
            "usage": usage,
            "estimated_cost_usd": _estimate_openai_cost_usd(model, usage),
        },
        latency_ms=0.0,
    )


def run_openai_with_context(case: BenchmarkCase, model: str) -> Prediction:
    from harness.framework_runners.common import list_case_files, serialized_case_materials

    prompt = build_contextual_prompt(case)
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    request = urllib.request.Request(
        _openai_chat_completions_url(),
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": "application/json",
            "User-Agent": DEFAULT_OPENAI_HTTP_USER_AGENT,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    choices = payload.get("choices", [])
    text = ""
    if choices:
        text = str(choices[0].get("message", {}).get("content", ""))
    answer = _extract_json_answer(text)
    usage = _openai_usage(payload)
    return Prediction(
        case_id=case.case_id,
        runner="openai_with_context",
        answer=answer,
        evidence={
            "model": model,
            "raw_response": text,
            "files_used": list_case_files(case),
            "materials": json.loads(serialized_case_materials(case)),
            "usage": usage,
            "estimated_cost_usd": _estimate_openai_cost_usd(model, usage),
        },
        latency_ms=0.0,
    )


def run_anthropic_raw_llm(case: BenchmarkCase, model: str) -> Prediction:
    body = {
        "model": model,
        "max_tokens": 256,
        "messages": [{"role": "user", "content": build_prompt(case)}],
    }
    request = urllib.request.Request(
        _anthropic_messages_url(),
        data=json.dumps(body).encode("utf-8"),
        headers=_anthropic_headers(),
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    blocks = payload.get("content", [])
    text = "\n".join(
        block.get("text", "") for block in blocks if isinstance(block, dict)
    ).strip()
    answer = _extract_json_answer(text)
    usage = _anthropic_usage(payload)
    return Prediction(
        case_id=case.case_id,
        runner="anthropic_raw_llm",
        answer=answer,
        evidence={
            "model": model,
            "raw_response": text,
            "usage": usage,
            "estimated_cost_usd": _estimate_anthropic_cost_usd(model, usage),
        },
        latency_ms=0.0,
    )


def run_anthropic_with_context(case: BenchmarkCase, model: str) -> Prediction:
    prompt = build_contextual_prompt(case)
    body = {
        "model": model,
        "max_tokens": 512,
        "messages": [{"role": "user", "content": prompt}],
    }
    request = urllib.request.Request(
        _anthropic_messages_url(),
        data=json.dumps(body).encode("utf-8"),
        headers=_anthropic_headers(),
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    blocks = payload.get("content", [])
    text = "\n".join(
        block.get("text", "") for block in blocks if isinstance(block, dict)
    ).strip()
    answer = _extract_json_answer(text)
    from harness.framework_runners.common import list_case_files, serialized_case_materials
    usage = _anthropic_usage(payload)

    return Prediction(
        case_id=case.case_id,
        runner="anthropic_with_context",
        answer=answer,
        evidence={
            "model": model,
            "raw_response": text,
            "files_used": list_case_files(case),
            "materials": json.loads(serialized_case_materials(case)),
            "usage": usage,
            "estimated_cost_usd": _estimate_anthropic_cost_usd(model, usage),
        },
        latency_ms=0.0,
    )


def validate_baseline_is_runnable(spec: BaselineSpec) -> None:
    missing = missing_env_vars(spec)
    if missing:
        raise RuntimeError(
            f"Baseline '{spec.baseline_id}' is not configured. Missing env vars: {', '.join(missing)}"
        )
