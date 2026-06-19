from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any

from harness.coaction_benchmark import BenchmarkCase, Prediction


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
            baseline_id="anthropic_raw_llm",
            label="Anthropic Raw LLM",
            category="llm_only",
            runner_kind="anthropic_raw_llm",
            provider="anthropic",
            model_env_var="ANTHROPIC_MODEL",
            default_model="claude-sonnet-4-0",
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
            baseline_id="react_agent",
            label="ReAct Agent",
            category="open_tooling",
            runner_kind="react_agent",
            provider=None,
            model_env_var=None,
            default_model=None,
            spreadsheet_basis="Approach / baseline: ReAct agent; Paper to read: ReAct",
            description="Open agent baseline with thought-action-observation loops and tool calls.",
            implementation_status="offline_ready",
            notes=[
                "Good open baseline for agentic tool-use.",
                "Runs today in a local offline wrapper mode; can later be replaced with a real framework-backed implementation.",
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
            implementation_status="offline_ready",
            notes=[
                "Good comparator for orchestration-heavy open tooling.",
                "Runs today in a local offline wrapper mode and can later be swapped for a real multi-agent implementation.",
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
            implementation_status="offline_ready",
            notes=[
                "Strong agentic architecture comparator for orchestration-heavy tasks.",
                "Good fit if we want a named open framework baseline rather than only a generic multi-agent pattern.",
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
            implementation_status="offline_ready",
            notes=[
                "Interesting comparator if we want to benchmark GP as an orchestrator.",
                "Heavier than ReAct, but a useful architecture-level baseline.",
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
            implementation_status="offline_ready",
            notes=[
                "Good basecase for realistic analytical querying without the full GP stack.",
                "Natural bridge between raw LLM baselines and multi-agent orchestration baselines.",
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
    return [name for name in spec.required_env_vars if not os.getenv(name)]


def _extract_json_answer(text: str) -> list[str]:
    try:
        payload = json.loads(text)
        if isinstance(payload, dict) and isinstance(payload.get("answer"), list):
            return [str(item) for item in payload["answer"]]
    except json.JSONDecodeError:
        pass
    stripped = text.strip()
    return [stripped] if stripped else []


def run_openai_raw_llm(case: BenchmarkCase, model: str) -> Prediction:
    body = {
        "model": model,
        "input": build_prompt(case),
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    text = payload.get("output_text", "")
    answer = _extract_json_answer(text)
    return Prediction(
        case_id=case.case_id,
        runner="openai_raw_llm",
        answer=answer,
        evidence={"model": model, "raw_response": text},
        latency_ms=0.0,
    )


def run_anthropic_raw_llm(case: BenchmarkCase, model: str) -> Prediction:
    body = {
        "model": model,
        "max_tokens": 256,
        "messages": [{"role": "user", "content": build_prompt(case)}],
    }
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    blocks = payload.get("content", [])
    text = "\n".join(
        block.get("text", "") for block in blocks if isinstance(block, dict)
    ).strip()
    answer = _extract_json_answer(text)
    return Prediction(
        case_id=case.case_id,
        runner="anthropic_raw_llm",
        answer=answer,
        evidence={"model": model, "raw_response": text},
        latency_ms=0.0,
    )


def validate_baseline_is_runnable(spec: BaselineSpec) -> None:
    missing = missing_env_vars(spec)
    if missing:
        raise RuntimeError(
            f"Baseline '{spec.baseline_id}' is not configured. Missing env vars: {', '.join(missing)}"
        )
