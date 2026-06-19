from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASELINES_ROOT = ROOT / "baselines"


@dataclass(frozen=True)
class ExternalBaselineRepo:
    repo_id: str
    label: str
    local_path: str
    upstream_url: str
    baseline_ids: list[str]
    recommended_role: str
    wrapper_strategy: str
    install_hint: str
    entrypoint_hint: str
    notes: list[str] = field(default_factory=list)


def get_external_repo_catalog() -> list[ExternalBaselineRepo]:
    return [
        ExternalBaselineRepo(
            repo_id="metagpt",
            label="MetaGPT",
            local_path="baselines/metagpt",
            upstream_url="https://github.com/FoundationAgents/MetaGPT.git",
            baseline_ids=[
                "metagpt_sop_agent",
                "multi_agent_analyst_coder_critic",
            ],
            recommended_role="SOP-style multi-agent baseline",
            wrapper_strategy="library_or_cli_wrapper",
            install_hint="Install the package in its own environment, then call either the CLI or a narrow library entrypoint.",
            entrypoint_hint="Prefer the Data Interpreter path for benchmark tasks instead of the full software-company workflow.",
            notes=[
                "Best fit for SOP-style orchestration.",
                "Likely heavier than the other repos because it expects its own config and wider dependencies.",
            ],
        ),
        ExternalBaselineRepo(
            repo_id="autogen",
            label="AutoGen",
            local_path="baselines/autogen",
            upstream_url="https://github.com/microsoft/autogen.git",
            baseline_ids=[
                "autogen_multi_agent",
                "react_agent",
            ],
            recommended_role="named multi-agent architecture baseline",
            wrapper_strategy="custom_team_wrapper",
            install_hint="Install the AgentChat and OpenAI extension packages in a dedicated environment, then run a small custom team script.",
            entrypoint_hint="Wrap AssistantAgent plus SelectorGroupChat or MagenticOneGroupChat in a benchmark adapter.",
            notes=[
                "Good for a thin custom benchmark team.",
                "Repo is useful as a reference and package source even if we do not adopt every built-in pattern.",
            ],
        ),
        ExternalBaselineRepo(
            repo_id="langgraph",
            label="LangGraph",
            local_path="baselines/langgraph",
            upstream_url="https://github.com/langchain-ai/langgraph.git",
            baseline_ids=[
                "single_agent_data_analyst",
            ],
            recommended_role="single-agent data-analysis architecture baseline",
            wrapper_strategy="graph_adapter_wrapper",
            install_hint="Install langgraph in a dedicated environment and construct a small benchmark graph around local file loading and answer formatting.",
            entrypoint_hint="Use a compact StateGraph-based wrapper rather than depending on archived examples.",
            notes=[
                "Probably the lightest architecture baseline to operationalize first.",
                "Good match for our current file-backed benchmark cases.",
            ],
        ),
    ]


def discover_external_repos() -> list[dict[str, Any]]:
    records = []
    for repo in get_external_repo_catalog():
        path = ROOT / repo.local_path
        records.append(
            {
                **asdict(repo),
                "exists_locally": path.exists(),
                "absolute_path": str(path),
                "readme_path": str(path / "README.md"),
            }
        )
    return records


def write_external_repo_catalog(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(discover_external_repos(), handle, indent=2)
