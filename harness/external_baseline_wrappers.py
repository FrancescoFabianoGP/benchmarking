from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from harness.external_baseline_repos import ROOT, discover_external_repos


@dataclass(frozen=True)
class WrapperPlan:
    baseline_id: str
    repo_id: str
    wrapper_name: str
    implementation_status: str
    recommended_env: str
    invocation_shape: str
    wrapper_inputs: list[str]
    wrapper_outputs: list[str]
    next_steps: list[str] = field(default_factory=list)


def get_wrapper_plans() -> list[WrapperPlan]:
    return [
        WrapperPlan(
            baseline_id="single_agent_data_analyst",
            repo_id="langgraph",
            wrapper_name="langgraph_single_agent_wrapper",
            implementation_status="ready_to_build",
            recommended_env="separate virtualenv or uv env for langgraph",
            invocation_shape="python module that consumes one benchmark case and returns the normalized answer JSON",
            wrapper_inputs=["case.prompt", "case.dataset", "local CSV paths"],
            wrapper_outputs=["answer", "trace", "tool events", "latency_ms"],
            next_steps=[
                "Create a tiny StateGraph with load_data, reason, and format_output nodes.",
                "Keep the first version local-file only with no web tools.",
            ],
        ),
        WrapperPlan(
            baseline_id="autogen_multi_agent",
            repo_id="autogen",
            wrapper_name="autogen_team_wrapper",
            implementation_status="ready_to_build",
            recommended_env="separate virtualenv or uv env with autogen-agentchat and autogen-ext[openai]",
            invocation_shape="python script that assembles a small analyst plus verifier team around the benchmark prompt",
            wrapper_inputs=["case.prompt", "optional local file reader tool"],
            wrapper_outputs=["answer", "team transcript", "latency_ms"],
            next_steps=[
                "Start with two AssistantAgent roles: analyst and verifier.",
                "Use a minimal group-chat or selector pattern before trying heavier orchestration.",
            ],
        ),
        WrapperPlan(
            baseline_id="react_agent",
            repo_id="autogen",
            wrapper_name="autogen_react_style_wrapper",
            implementation_status="ready_to_build",
            recommended_env="same environment as AutoGen multi-agent",
            invocation_shape="single assistant agent with a small local file-reading toolset",
            wrapper_inputs=["case.prompt", "local benchmark asset paths"],
            wrapper_outputs=["answer", "tool calls", "latency_ms"],
            next_steps=[
                "Constrain the tool surface to reading the benchmark tables and cache files.",
                "Keep the prompt and output schema aligned with the raw LLM baselines.",
            ],
        ),
        WrapperPlan(
            baseline_id="metagpt_sop_agent",
            repo_id="metagpt",
            wrapper_name="metagpt_data_interpreter_wrapper",
            implementation_status="ready_to_build",
            recommended_env="separate virtualenv or uv env for metagpt",
            invocation_shape="python module using the Data Interpreter path for case-by-case analysis",
            wrapper_inputs=["case.prompt", "materialized local benchmark files"],
            wrapper_outputs=["answer", "interpreter transcript", "latency_ms"],
            next_steps=[
                "Avoid the full software-company workflow for the benchmark.",
                "Use the narrower data-interpreter route for analytical tasks.",
            ],
        ),
        WrapperPlan(
            baseline_id="multi_agent_analyst_coder_critic",
            repo_id="metagpt",
            wrapper_name="metagpt_multi_role_wrapper",
            implementation_status="concept_ready",
            recommended_env="same environment as MetaGPT",
            invocation_shape="small custom role bundle mapped to analyst, coder, and critic responsibilities",
            wrapper_inputs=["case.prompt", "optional file-reading tool"],
            wrapper_outputs=["answer", "role transcript", "latency_ms"],
            next_steps=[
                "Only build this after the single-agent and AutoGen wrappers work.",
                "This is valuable, but it is not the cheapest baseline to operationalize first.",
            ],
        ),
    ]


def wrapper_manifest() -> list[dict[str, Any]]:
    repo_by_id = {item["repo_id"]: item for item in discover_external_repos()}
    records = []
    for plan in get_wrapper_plans():
        repo = repo_by_id.get(plan.repo_id, {})
        records.append(
            {
                **asdict(plan),
                "repo_exists_locally": repo.get("exists_locally", False),
                "repo_path": repo.get("absolute_path"),
            }
        )
    return records

