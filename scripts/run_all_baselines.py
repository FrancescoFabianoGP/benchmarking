from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.env_loader import load_local_env

load_local_env()

from harness.baseline_registry import get_baseline_catalog
DEFAULT_REPORT_ROOT = ROOT / "reports" / "runs" / "all_baselines"


def _apply_fast_defaults() -> None:
    os.environ.setdefault("OPENAI_MODEL", "gpt-4o-mini")
    os.environ.setdefault("BENCHMARK_FRAMEWORK_MODEL", "gpt-4o-mini")
    os.environ.setdefault("LANGGRAPH_MODEL", "gpt-4o-mini")
    os.environ.setdefault("AUTOGEN_REACT_MODEL", "gpt-4o-mini")
    os.environ.setdefault("AUTOGEN_MULTI_AGENT_MODEL", "gpt-4o-mini")
    os.environ.setdefault("METAGPT_MODEL", "gpt-4o-mini")
    os.environ.setdefault("ANTHROPIC_MODEL", "claude-sonnet-4-6")


def _summary_row(result: dict[str, Any]) -> dict[str, Any]:
    summary = result.get("summary", {})
    return {
        "status": "ok",
        "runner": summary.get("runner"),
        "accuracy": summary.get("overall_accuracy"),
        "cases": summary.get("case_count"),
        "avg_latency_ms": summary.get("average_latency_ms"),
        "total_tokens": summary.get("total_tokens"),
        "estimated_cost_usd": summary.get("total_estimated_cost_usd"),
        "report_dir": result.get("report_dir"),
    }


def _error_row(exc: Exception) -> dict[str, Any]:
    return {
        "status": "error",
        "error": str(exc),
    }


def _timeout_row(timeout_seconds: int) -> dict[str, Any]:
    return {
        "status": "timeout",
        "error": f"Timed out after {timeout_seconds} seconds",
    }


def _scores_path(report_root: Path, baseline_id: str) -> Path:
    return report_root / baseline_id / "scores.json"


def _load_summary_from_scores(report_root: Path, baseline_id: str) -> dict[str, Any]:
    scores_path = _scores_path(report_root, baseline_id)
    if not scores_path.exists():
        raise FileNotFoundError(f"Expected score file not found: {scores_path}")
    with scores_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return {
        "summary": payload.get("summary", {}),
        "report_dir": str(scores_path.parent),
    }


def _model_label(baseline_id: str) -> str:
    if baseline_id == "structured_lookup":
        return "deterministic lookup"
    if baseline_id in {"openai_raw_llm", "openai_with_context"}:
        return os.getenv("OPENAI_MODEL", "gpt-5")
    if baseline_id in {"anthropic_raw_llm", "anthropic_with_context"}:
        return os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    if baseline_id == "react_agent":
        return os.getenv(
            "AUTOGEN_REACT_MODEL",
            os.getenv("BENCHMARK_FRAMEWORK_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
        )
    if baseline_id == "autogen_multi_agent":
        return os.getenv(
            "AUTOGEN_MULTI_AGENT_MODEL",
            os.getenv("BENCHMARK_FRAMEWORK_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
        )
    if baseline_id == "single_agent_data_analyst":
        return os.getenv(
            "LANGGRAPH_MODEL",
            os.getenv("BENCHMARK_FRAMEWORK_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
        )
    if baseline_id in {"metagpt_sop_agent", "multi_agent_analyst_coder_critic"}:
        return os.getenv(
            "METAGPT_MODEL",
            os.getenv("BENCHMARK_FRAMEWORK_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
        )
    if baseline_id == "gp_zeus_venue_risk":
        return "zeus workflow"
    return "default"


def _write_outputs(report_root: Path, benchmark_id: str, rows: dict[str, dict[str, Any]]) -> None:
    report_root.mkdir(parents=True, exist_ok=True)
    payload = {
        "benchmark_id": benchmark_id,
        "baselines": rows,
    }
    with (report_root / "suite_status.json").open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    lines = [
        "# Baseline Suite Status",
        "",
        f"- Benchmark: `{benchmark_id}`",
        "",
        "| Baseline | Status | Accuracy | Avg Latency (ms) | Tokens | Est. Cost (USD) | Notes |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for baseline_id, row in rows.items():
        if row["status"] == "ok":
            lines.append(
                "| {baseline_id} | ok | {accuracy} | {latency} | {tokens} | {cost} | {report_dir} |".format(
                    baseline_id=baseline_id,
                    accuracy=f"{row['accuracy']:.1%}" if isinstance(row.get("accuracy"), (int, float)) else "n/a",
                    latency=f"{row['avg_latency_ms']:.2f}" if isinstance(row.get("avg_latency_ms"), (int, float)) else "n/a",
                    tokens=row.get("total_tokens", "n/a") if row.get("total_tokens") is not None else "n/a",
                    cost=f"{row['estimated_cost_usd']:.6f}" if isinstance(row.get("estimated_cost_usd"), (int, float)) else "n/a",
                    report_dir=row.get("report_dir", ""),
                )
            )
        else:
            lines.append(
                f"| {baseline_id} | error | n/a | n/a | n/a | n/a | {str(row.get('error', '')).replace('|', '/')} |"
            )

    with (report_root / "suite_status.md").open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run all registered baselines sequentially and keep going on failures."
    )
    parser.add_argument("--benchmark", default="coaction_venue_risk")
    parser.add_argument("--baseline", action="append", help="Optional baseline IDs to run.")
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=600,
        help="Per-baseline timeout in seconds.",
    )
    parser.add_argument(
        "--profile",
        choices=["fast", "current"],
        default="fast",
        help="Use fast model defaults unless explicit environment variables already override them.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.profile == "fast":
        _apply_fast_defaults()

    baseline_ids = (
        args.baseline
        if args.baseline
        else [spec.baseline_id for spec in get_baseline_catalog()]
    )

    rows: dict[str, dict[str, Any]] = {}
    total = len(baseline_ids)
    for index, baseline_id in enumerate(baseline_ids, start=1):
        report_dir = args.report_root / baseline_id
        print(
            "[suite] starting {index}/{total} baseline={baseline} model={model} report_dir={report_dir}".format(
                index=index,
                total=total,
                baseline=baseline_id,
                model=_model_label(baseline_id),
                report_dir=report_dir,
            ),
            flush=True,
        )
        try:
            child_env = os.environ.copy()
            child_env.setdefault("BENCHMARK_PROGRESS", "1")
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "run_benchmark.py"),
                    "--benchmark",
                    args.benchmark,
                    "--baseline",
                    baseline_id,
                    "--report-dir",
                    str(report_dir),
                ],
                cwd=ROOT,
                env=child_env,
                text=True,
                timeout=args.timeout_seconds,
                check=True,
            )
            result = _load_summary_from_scores(args.report_root, baseline_id)
            rows[baseline_id] = _summary_row(result)
            summary = rows[baseline_id]
            print(
                "[suite] completed baseline={baseline} status=ok accuracy={accuracy} avg_latency_ms={latency}".format(
                    baseline=baseline_id,
                    accuracy=(
                        f"{summary['accuracy']:.1%}"
                        if isinstance(summary.get("accuracy"), (int, float))
                        else "n/a"
                    ),
                    latency=(
                        f"{summary['avg_latency_ms']:.2f}"
                        if isinstance(summary.get("avg_latency_ms"), (int, float))
                        else "n/a"
                    ),
                ),
                flush=True,
            )
        except subprocess.TimeoutExpired:
            rows[baseline_id] = _timeout_row(args.timeout_seconds)
            print(
                f"[suite] completed baseline={baseline_id} status=timeout timeout_seconds={args.timeout_seconds}",
                flush=True,
            )
        except subprocess.CalledProcessError as exc:
            details = str(exc)
            rows[baseline_id] = {
                "status": "error",
                "error": details,
            }
            print(
                f"[suite] completed baseline={baseline_id} status=error details={details}",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            rows[baseline_id] = _error_row(exc)
            print(
                f"[suite] completed baseline={baseline_id} status=error details={exc}",
                flush=True,
            )

    _write_outputs(args.report_root, args.benchmark, rows)
    print(json.dumps({"benchmark_id": args.benchmark, "baselines": rows}, indent=2))


if __name__ == "__main__":
    main()
