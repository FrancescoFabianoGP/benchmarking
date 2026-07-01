from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import SourceMatchTermination
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient

from harness.framework_runners.common import (
    autogen_openai_client_kwargs,
    framework_model_name,
    list_available_sources_tool,
    parse_answer_text,
    read_case_from_stdin,
    read_relevant_court_stats,
    read_relevant_judge_stats,
    read_relevant_summaries,
    serialize_message,
    tool_instructions,
)


async def run_case() -> dict[str, Any]:
    case = read_case_from_stdin()

    def list_available_sources() -> dict[str, Any]:
        return list_available_sources_tool(case)

    def read_court_stats() -> dict[str, Any]:
        return read_relevant_court_stats(case)

    def read_judge_stats() -> dict[str, Any]:
        return read_relevant_judge_stats(case)

    def read_summaries() -> dict[str, Any]:
        return read_relevant_summaries(case)

    model_name = framework_model_name("AUTOGEN_MULTI_AGENT_MODEL")
    client_kwargs = autogen_openai_client_kwargs("AUTOGEN_MULTI_AGENT_MODEL")
    analyst_client = OpenAIChatCompletionClient(**client_kwargs)
    verifier_client = OpenAIChatCompletionClient(**client_kwargs)
    summarizer_client = OpenAIChatCompletionClient(**client_kwargs)

    analyst = AssistantAgent(
        name="analyst",
        description="Inspects the benchmark sources and proposes an answer.",
        model_client=analyst_client,
        tools=[list_available_sources, read_court_stats, read_judge_stats, read_summaries],
        reflect_on_tool_use=True,
        max_tool_iterations=4,
        system_message="\n".join(
            [
                tool_instructions(case),
                "You are the analyst. Inspect the sources and explain the best candidate answer for the verifier.",
            ]
        ),
    )
    verifier = AssistantAgent(
        name="verifier",
        description="Checks the analyst's proposal against the source data.",
        model_client=verifier_client,
        tools=[read_court_stats, read_judge_stats, read_summaries],
        reflect_on_tool_use=True,
        max_tool_iterations=3,
        system_message="\n".join(
            [
                tool_instructions(case),
                "You are the verifier. Challenge weak claims and confirm the best supported answer.",
            ]
        ),
    )
    summarizer = AssistantAgent(
        name="summarizer",
        description="Publishes the final normalized benchmark answer.",
        model_client=summarizer_client,
        system_message="\n".join(
            [
                tool_instructions(case),
                "You are the summarizer. Read the analyst and verifier messages and return only final JSON.",
            ]
        ),
    )

    team = RoundRobinGroupChat(
        participants=[analyst, verifier, summarizer],
        termination_condition=SourceMatchTermination(sources=["summarizer"]),
    )

    started = perf_counter()
    try:
        result: TaskResult = await team.run(task=case.prompt)
    finally:
        await analyst_client.close()
        await verifier_client.close()
        await summarizer_client.close()
    latency_ms = (perf_counter() - started) * 1000
    final_message = result.messages[-1]
    final_text = final_message.content if isinstance(final_message, TextMessage) else str(final_message)
    return {
        "answer": parse_answer_text(final_text),
        "evidence": {
            "framework": "autogen",
            "variant": "multi_agent_team_live",
            "model": model_name,
            "message_trace": [serialize_message(message) for message in result.messages],
            "participants": ["analyst", "verifier", "summarizer"],
        },
        "latency_ms": latency_ms,
    }


def main() -> None:
    json.dump(asyncio.run(run_case()), fp=sys.stdout)


if __name__ == "__main__":
    main()
