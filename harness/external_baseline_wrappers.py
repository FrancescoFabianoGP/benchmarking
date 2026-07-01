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
            implementation_status="framework_wrapper_requires_runtime",
            recommended_env="repo-local virtualenv under .baseline_envs/langgraph",
            invocation_shape="python wrapper that builds a small LangGraph flow for one benchmark case and returns normalized answer JSON",
            wrapper_inputs=["case.prompt", "case.dataset", "local CSV paths"],
            wrapper_outputs=["answer", "trace", "tool events", "latency_ms"],
            next_steps=[
                "Install the vendored LangGraph packages with `python3 scripts/install_baseline_runtimes.py --framework langgraph`.",
                "Run the local-file-only wrapper in `harness/framework_runners/langgraph_single_agent.py` through the harness.",
            ],
        ),
        WrapperPlan(
            baseline_id="autogen_multi_agent",
            repo_id="autogen",
            wrapper_name="autogen_team_wrapper",
            implementation_status="framework_wrapper_requires_runtime",
            recommended_env="repo-local virtualenv under .baseline_envs/autogen",
            invocation_shape="python wrapper that assembles a small AutoGen analyst plus verifier team around one benchmark prompt",
            wrapper_inputs=["case.prompt", "optional local file reader tool"],
            wrapper_outputs=["answer", "team transcript", "latency_ms"],
            next_steps=[
                "Install the vendored AutoGen packages with `python3 scripts/install_baseline_runtimes.py --framework autogen`.",
                "Run `harness/framework_runners/autogen_multi_agent.py` through the harness.",
            ],
        ),
        WrapperPlan(
            baseline_id="react_agent",
            repo_id="autogen",
            wrapper_name="autogen_react_style_wrapper",
            implementation_status="framework_wrapper_requires_runtime",
            recommended_env="repo-local virtualenv under .baseline_envs/autogen",
            invocation_shape="single AutoGen assistant agent with a small local file-reading toolset",
            wrapper_inputs=["case.prompt", "local benchmark asset paths"],
            wrapper_outputs=["answer", "tool calls", "latency_ms"],
            next_steps=[
                "Install the vendored AutoGen packages with `python3 scripts/install_baseline_runtimes.py --framework autogen`.",
                "Run `harness/framework_runners/autogen_react_agent.py` through the harness.",
            ],
        ),
        WrapperPlan(
            baseline_id="metagpt_sop_agent",
            repo_id="metagpt",
            wrapper_name="metagpt_data_interpreter_wrapper",
            implementation_status="framework_wrapper_requires_runtime",
            recommended_env="repo-local virtualenv under .baseline_envs/metagpt",
            invocation_shape="python wrapper that runs a live MetaGPT Data Interpreter path for one benchmark case",
            wrapper_inputs=["case.prompt", "materialized local benchmark files"],
            wrapper_outputs=["answer", "interpreter transcript", "latency_ms"],
            next_steps=[
                "Install the vendored MetaGPT packages with `python3 scripts/install_baseline_runtimes.py --framework metagpt`.",
                "Run `harness/framework_runners/metagpt_wrappers.py` through the harness.",
            ],
        ),
        WrapperPlan(
            baseline_id="multi_agent_analyst_coder_critic",
            repo_id="metagpt",
            wrapper_name="metagpt_multi_role_wrapper",
            implementation_status="framework_wrapper_requires_runtime",
            recommended_env="repo-local virtualenv under .baseline_envs/metagpt",
            invocation_shape="small custom MetaGPT role bundle mapped to analyst, coder, and critic responsibilities",
            wrapper_inputs=["case.prompt", "optional file-reading tool"],
            wrapper_outputs=["answer", "role transcript", "latency_ms"],
            next_steps=[
                "Install the vendored MetaGPT packages with `python3 scripts/install_baseline_runtimes.py --framework metagpt`.",
                "Run `harness/framework_runners/metagpt_wrappers.py` through the harness with the multi-role baseline id.",
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
