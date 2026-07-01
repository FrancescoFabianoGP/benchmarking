from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, TypedDict

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.benchmark_types import BenchmarkCase
from harness.framework_runners.common import (
    case_materials,
    estimate_openai_cost_usd,
    framework_model_name,
    openai_usage,
    openai_text_completion,
    parse_answer_text,
    tool_instructions,
)


class GraphState(TypedDict, total=False):
    case: dict[str, Any]
    materials: dict[str, Any]
    analysis: str
    answer: list[str]
    trace: list[dict[str, Any]]


@dataclass
class WrapperResult:
    answer: list[str]
    evidence: dict[str, Any]
    latency_ms: float


def _load_materials(state: GraphState) -> GraphState:
    case = BenchmarkCase(**state["case"])
    materials = case_materials(case)
    return {
        "materials": materials,
        "trace": state["trace"]
        + [
            {
                "node": "load_materials",
                "detail": {
                    "dataset": case.dataset,
                    "files": materials["case"]["allowed_sources"],
                },
            }
        ],
    }


def _run_live_analysis(state: GraphState) -> GraphState:
    case = BenchmarkCase(**state["case"])
    model = framework_model_name("LANGGRAPH_MODEL")
    prompt = "\n\n".join(
        [
            tool_instructions(case),
            "Inspect the benchmark materials below and reason about the correct answer.",
            json.dumps(state["materials"], indent=2, sort_keys=True),
        ]
    )
    output_text, payload = openai_text_completion(
        prompt=prompt,
        model=model,
        system_prompt="You are a careful data-analysis agent running inside a LangGraph workflow.",
    )
    usage = openai_usage(payload)
    answer = parse_answer_text(output_text)
    return {
        "analysis": output_text,
        "answer": answer,
        "usage": usage,
        "trace": state["trace"]
        + [
            {
                "node": "run_live_analysis",
                "detail": {
                    "model": model,
                    "answer": answer,
                    "response_id": payload.get("id", ""),
                    "usage": usage,
                },
            }
        ],
    }


def _format_output(state: GraphState) -> GraphState:
    return {
        "trace": state["trace"] + [{"node": "format_output", "detail": state["answer"]}],
    }


def run_langgraph_case(case: BenchmarkCase) -> WrapperResult:
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(GraphState)
    graph.add_node("load_materials", _load_materials)
    graph.add_node("run_live_analysis", _run_live_analysis)
    graph.add_node("format_output", _format_output)
    graph.add_edge(START, "load_materials")
    graph.add_edge("load_materials", "run_live_analysis")
    graph.add_edge("run_live_analysis", "format_output")
    graph.add_edge("format_output", END)

    started = perf_counter()
    result = graph.compile().invoke({"case": asdict(case), "trace": []})
    latency_ms = (perf_counter() - started) * 1000

    return WrapperResult(
        answer=result["answer"],
        evidence={
            "framework": "langgraph",
            "variant": "single_agent_live",
            "model": framework_model_name("LANGGRAPH_MODEL"),
            "materials": result["materials"],
            "analysis": result["analysis"],
            "trace": result["trace"],
            "usage": result.get("usage", {}),
            "estimated_cost_usd": estimate_openai_cost_usd(
                framework_model_name("LANGGRAPH_MODEL"),
                result.get("usage", {}),
            ),
        },
        latency_ms=latency_ms,
    )


def main() -> None:
    payload = json.load(sys.stdin)
    case = BenchmarkCase(**payload["case"])
    result = run_langgraph_case(case)
    json.dump(
        {
            "answer": result.answer,
            "evidence": result.evidence,
            "latency_ms": result.latency_ms,
        },
        sys.stdout,
    )


if __name__ == "__main__":
    main()
