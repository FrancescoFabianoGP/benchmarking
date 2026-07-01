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
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient

from harness.framework_runners.common import (
    framework_model_name,
    list_available_sources_tool,
    openai_base_url,
    parse_answer_text,
    read_case_from_stdin,
    read_relevant_court_stats,
    read_relevant_judge_stats,
    read_relevant_summaries,
    require_openai_api_key,
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

    model_client = OpenAIChatCompletionClient(
        model=framework_model_name("AUTOGEN_REACT_MODEL"),
        api_key=require_openai_api_key(),
        base_url=openai_base_url(),
    )

    agent = AssistantAgent(
        name="react_agent",
        description="A live tool-using benchmark agent.",
        model_client=model_client,
        tools=[list_available_sources, read_court_stats, read_judge_stats, read_summaries],
        reflect_on_tool_use=True,
        max_tool_iterations=6,
        system_message=tool_instructions(case),
    )

    started = perf_counter()
    try:
        result: TaskResult = await agent.run(task=case.prompt)
    finally:
        await model_client.close()
    latency_ms = (perf_counter() - started) * 1000
    final_message = result.messages[-1]
    final_text = final_message.content if isinstance(final_message, TextMessage) else str(final_message)
    return {
        "answer": parse_answer_text(final_text),
        "evidence": {
            "framework": "autogen",
            "variant": "react_agent_live",
            "model": framework_model_name("AUTOGEN_REACT_MODEL"),
            "message_trace": [serialize_message(message) for message in result.messages],
        },
        "latency_ms": latency_ms,
    }


def main() -> None:
    json.dump(asyncio.run(run_case()), fp=sys.stdout)


if __name__ == "__main__":
    main()
