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

from metagpt.actions import Action
from metagpt.actions.add_requirement import UserRequirement
from metagpt.environment import Environment
from metagpt.roles import Role
from metagpt.roles.di.data_interpreter import DataInterpreter
from metagpt.schema import Message
from metagpt.team import Team
from metagpt.tools.tool_registry import register_tool

from harness.benchmark_types import BenchmarkCase
from harness.framework_runners.common import (
    case_materials,
    framework_model_name,
    list_available_sources_tool,
    parse_answer_text,
    read_relevant_court_stats,
    read_relevant_judge_stats,
    read_relevant_summaries,
    tool_instructions,
)

_ACTIVE_CASE: BenchmarkCase | None = None


def _require_active_case() -> BenchmarkCase:
    if _ACTIVE_CASE is None:
        raise RuntimeError("No active benchmark case is set for MetaGPT tools.")
    return _ACTIVE_CASE


@register_tool()
def list_benchmark_sources() -> dict[str, Any]:
    case = _require_active_case()
    return list_available_sources_tool(case)


@register_tool()
def read_benchmark_court_stats() -> dict[str, Any]:
    case = _require_active_case()
    return read_relevant_court_stats(case)


@register_tool()
def read_benchmark_judge_stats() -> dict[str, Any]:
    case = _require_active_case()
    return read_relevant_judge_stats(case)


@register_tool()
def read_benchmark_summaries() -> dict[str, Any]:
    case = _require_active_case()
    return read_relevant_summaries(case)


def _set_active_case(case: BenchmarkCase) -> None:
    global _ACTIVE_CASE
    _ACTIVE_CASE = case


def _message_trace(messages: list[Any]) -> list[dict[str, Any]]:
    trace = []
    for message in messages:
        trace.append(
            {
                "type": type(message).__name__,
                "source": getattr(message, "sent_from", getattr(message, "source", "")),
                "content": getattr(message, "content", str(message)),
                "cause_by": str(getattr(message, "cause_by", "")),
                "send_to": sorted(getattr(message, "send_to", []) or []),
            }
        )
    return trace


class AnalystReview(Action):
    case_description: str
    materials_json: str

    async def run(self, *args, **kwargs) -> Message:
        del kwargs
        history = "\n".join(str(arg) for arg in args if arg)
        prompt = "\n\n".join(
            [
                self.case_description,
                "You are the analyst. Inspect the benchmark materials and propose the best answer candidate.",
                self.materials_json,
                f"Team history:\n{history}" if history else "",
                'Return JSON with keys "candidate_answer", "supporting_evidence", and "notes".',
            ]
        )
        response = await self._aask(prompt)
        return Message(content=response, sent_from="Analyst", send_to={"Coder", "Critic"})


class CoderEvidence(Action):
    case_description: str
    materials_json: str

    async def run(self, *args, **kwargs) -> Message:
        del kwargs
        history = "\n".join(str(arg) for arg in args if arg)
        prompt = "\n\n".join(
            [
                self.case_description,
                "You are the coder. Re-check the data and package concrete evidence for the candidate answer.",
                self.materials_json,
                f"Team history:\n{history}" if history else "",
                'Return JSON with keys "validated_answer", "supporting_rows", and "warnings".',
            ]
        )
        response = await self._aask(prompt)
        return Message(content=response, sent_from="Coder", send_to={"Critic"})


class CriticFinalize(Action):
    case_description: str
    materials_json: str

    async def run(self, *args, **kwargs) -> Message:
        del kwargs
        history = "\n".join(str(arg) for arg in args if arg)
        prompt = "\n\n".join(
            [
                self.case_description,
                "You are the critic. Read the team history and publish the final benchmark answer.",
                self.materials_json,
                f"Team history:\n{history}" if history else "",
                'Return only JSON with the shape {"answer": ["..."]}.',
            ]
        )
        response = await self._aask(prompt)
        return Message(content=response, sent_from="Critic")


async def run_metagpt_sop(case: BenchmarkCase) -> dict[str, Any]:
    _set_active_case(case)
    materials = case_materials(case)
    role = DataInterpreter(
        react_mode="react",
        use_reflection=True,
        tools=[
            "list_benchmark_sources",
            "read_benchmark_court_stats",
            "read_benchmark_judge_stats",
            "read_benchmark_summaries",
        ],
    )

    prompt = "\n\n".join(
        [
            tool_instructions(case),
            "Use the benchmark tools to inspect the local data before answering.",
            "If you need evidence, call the tools instead of guessing.",
        ]
    )

    started = perf_counter()
    final_result = await role.run(prompt)
    latency_ms = (perf_counter() - started) * 1000

    final_text = getattr(final_result, "content", str(final_result))
    return {
        "answer": parse_answer_text(final_text),
        "evidence": {
            "framework": "metagpt",
            "variant": "data_interpreter_live",
            "model": framework_model_name("METAGPT_MODEL"),
            "materials": materials,
            "message_trace": _message_trace(role.get_memories()),
        },
        "latency_ms": latency_ms,
    }


async def run_metagpt_team(case: BenchmarkCase) -> dict[str, Any]:
    _set_active_case(case)
    materials_json = json.dumps(case_materials(case), indent=2, sort_keys=True)
    case_description = tool_instructions(case)

    analyst = Role(
        name="Analyst",
        profile="Analyst",
        goal="Inspect the benchmark data and propose the best answer candidate.",
        actions=[AnalystReview(case_description=case_description, materials_json=materials_json)],
    )
    analyst._watch([UserRequirement])

    coder = Role(
        name="Coder",
        profile="Coder",
        goal="Validate the analyst's proposal against the benchmark materials.",
        actions=[CoderEvidence(case_description=case_description, materials_json=materials_json)],
    )
    coder._watch([AnalystReview])

    critic = Role(
        name="Critic",
        profile="Critic",
        goal="Challenge weak claims and publish the final answer.",
        actions=[CriticFinalize(case_description=case_description, materials_json=materials_json)],
    )
    critic._watch([AnalystReview, CoderEvidence])

    team = Team(
        env=Environment(),
        use_mgx=False,
        roles=[analyst, coder, critic],
    )

    started = perf_counter()
    history_memory = await team.run(n_round=1, idea=case.prompt, auto_archive=False)
    latency_ms = (perf_counter() - started) * 1000
    history = history_memory.get()
    final_message = history[-1]
    return {
        "answer": parse_answer_text(final_message.content),
        "evidence": {
            "framework": "metagpt",
            "variant": "analyst_coder_critic_team_live",
            "model": framework_model_name("METAGPT_MODEL"),
            "message_trace": _message_trace(history),
            "participants": ["Analyst", "Coder", "Critic"],
        },
        "latency_ms": latency_ms,
    }


def run_payload(payload: dict[str, Any]) -> dict[str, Any]:
    baseline_id = payload["baseline_id"]
    case = BenchmarkCase(**payload["case"])
    if baseline_id == "metagpt_sop_agent":
        return asyncio.run(run_metagpt_sop(case))
    if baseline_id == "multi_agent_analyst_coder_critic":
        return asyncio.run(run_metagpt_team(case))
    raise ValueError(f"Unsupported MetaGPT baseline: {baseline_id}")


def main() -> None:
    if "--server" in sys.argv:
        for line in sys.stdin:
            if not line.strip():
                continue
            result = run_payload(json.loads(line))
            sys.stdout.write(json.dumps(result) + "\n")
            sys.stdout.flush()
        return

    payload = json.load(sys.stdin)
    json.dump(run_payload(payload), sys.stdout)


if __name__ == "__main__":
    main()
