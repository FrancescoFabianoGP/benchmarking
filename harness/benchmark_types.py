from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class BenchmarkCase:
    case_id: str
    dataset: str
    query_type: str
    metric_key: str
    prompt: str
    gold_answer: list[str]
    evidence: dict[str, Any]
    metadata: dict[str, Any]


@dataclass
class Prediction:
    case_id: str
    runner: str
    answer: list[str]
    evidence: dict[str, Any]
    latency_ms: float


@dataclass
class CaseScore:
    case_id: str
    runner: str
    is_correct: bool
    expected: list[str]
    predicted: list[str]
