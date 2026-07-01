from __future__ import annotations

import json
import os
import re
import subprocess
import ast
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from harness.baseline_registry import (
    configured_model_name,
    missing_env_vars,
    resolve_baseline,
    run_anthropic_raw_llm,
    run_anthropic_with_context,
    run_openai_raw_llm,
    run_openai_with_context,
)
from harness.benchmark_types import (
    BenchmarkCase,
    Prediction,
)
from harness.benchmarks.coaction_venue_risk import (
    overall_judge_rows,
    personal_injury_overall_rows,
    top_counties_by_metric,
    top_judges_for_county,
)
from harness.external_baseline_repos import discover_external_repos

ROOT = Path(__file__).resolve().parents[1]
LANGGRAPH_SINGLE_AGENT_WRAPPER = ROOT / "harness" / "framework_runners" / "langgraph_single_agent.py"
AUTOGEN_REACT_WRAPPER = ROOT / "harness" / "framework_runners" / "autogen_react_agent.py"
AUTOGEN_MULTI_AGENT_WRAPPER = ROOT / "harness" / "framework_runners" / "autogen_multi_agent.py"
METAGPT_WRAPPER = ROOT / "harness" / "framework_runners" / "metagpt_wrappers.py"
ZEUS_VENUE_RISK_WRAPPER = ROOT / "harness" / "framework_runners" / "zeus_venue_risk.py"
METAGPT_HOME = ROOT / ".baseline_envs" / "metagpt-home"
LOCAL_WORKFLOW_CACHE_ROOT = ROOT / ".benchmark_cache"


@dataclass(frozen=True)
class FrameworkRuntime:
    framework_id: str
    python_path: Path


FRAMEWORK_RUNTIMES = {
    "single_agent_data_analyst": FrameworkRuntime(
        framework_id="langgraph",
        python_path=ROOT / ".baseline_envs" / "langgraph" / "bin" / "python",
    ),
    "react_agent": FrameworkRuntime(
        framework_id="autogen",
        python_path=ROOT / ".baseline_envs" / "autogen" / "bin" / "python",
    ),
    "autogen_multi_agent": FrameworkRuntime(
        framework_id="autogen",
        python_path=ROOT / ".baseline_envs" / "autogen" / "bin" / "python",
    ),
    "metagpt_sop_agent": FrameworkRuntime(
        framework_id="metagpt",
        python_path=ROOT / ".baseline_envs" / "metagpt" / "bin" / "python",
    ),
    "multi_agent_analyst_coder_critic": FrameworkRuntime(
        framework_id="metagpt",
        python_path=ROOT / ".baseline_envs" / "metagpt" / "bin" / "python",
    ),
    "gp_zeus_venue_risk": FrameworkRuntime(
        framework_id="zeus",
        python_path=ROOT / ".baseline_envs" / "zeus" / "bin" / "python",
    ),
}
_PERSISTENT_WRAPPERS: dict[tuple[str, str], subprocess.Popen[str]] = {}


@dataclass(frozen=True)
class BaselineExecutionContext:
    baseline_id: str
    spec_notes: list[str]
    repo_path: str | None
    mode: str


def _repo_path_for_baseline(baseline_id: str) -> str | None:
    if baseline_id == "gp_zeus_venue_risk":
        return str(ROOT / "GP_components" / "zeus-service")
    for repo in discover_external_repos():
        if baseline_id in repo["baseline_ids"]:
            return repo["absolute_path"]
    return None


def _cloudflare_gateway_base_url_from_env(env: dict[str, str]) -> str | None:
    explicit = env.get("CLOUDFLARE_ZDR_AI_GATEWAY_BASE_URL")
    if explicit:
        return explicit.rstrip("/")

    for key in ("OPENAI_BASE_URL", "ANTHROPIC_BASE_URL"):
        configured = env.get(key)
        if not configured:
            continue
        trimmed = configured.rstrip("/")
        for suffix in ("/openai", "/anthropic"):
            if trimmed.endswith(suffix):
                return trimmed[: -len(suffix)]
        return trimmed
    return None


def _wrapper_timeout_seconds(runtime: FrameworkRuntime) -> float:
    raw_value = os.getenv("BENCHMARK_WRAPPER_TIMEOUT_SECONDS")
    if raw_value:
        try:
            return float(raw_value)
        except ValueError:
            pass
    if runtime.framework_id == "zeus":
        return 300.0
    return 120.0


def _seed_zeus_workflow_cache() -> None:
    source_cache_root = ROOT / "cases" / "coaction_venue_risk" / "data" / "cache"
    target_cache_root = LOCAL_WORKFLOW_CACHE_ROOT / "coaction" / "cache"
    if not source_cache_root.exists():
        return

    target_cache_root.mkdir(parents=True, exist_ok=True)
    for filename in (
        "all_jurisdiction_summary.json",
        "county_specific_summary.json",
        "venue_risk_litigation_highlights.json",
    ):
        source = source_cache_root / filename
        target = target_cache_root / filename
        if source.exists() and not target.exists():
            shutil.copy2(source, target)


def _execution_context(baseline_id: str, mode: str) -> BaselineExecutionContext:
    spec = resolve_baseline(baseline_id)
    return BaselineExecutionContext(
        baseline_id=baseline_id,
        spec_notes=spec.notes,
        repo_path=_repo_path_for_baseline(baseline_id),
        mode=mode,
    )


def _lookup_answer(case: BenchmarkCase, reference_data: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    if case.query_type == "county_metric_extreme":
        rows = personal_injury_overall_rows(reference_data["court_rows"][case.dataset])
        answer, metric_value = top_counties_by_metric(
            rows,
            case.metric_key,
            case.metadata["extreme"],
        )
        return answer, {
            "source_table": f"{case.dataset}/Court Analysis Stats.csv",
            "supporting_value": metric_value,
        }
    if case.query_type == "county_top_judge_dismissal_rate":
        rows = overall_judge_rows(reference_data["judge_rows"][case.dataset])
        answer, metric_value = top_judges_for_county(rows, case.evidence["county"])
        return answer, {
            "source_table": f"{case.dataset}/Judge MTD Rate.csv",
            "supporting_value": metric_value,
            "county": case.evidence["county"],
        }
    raise ValueError(f"Unsupported query type: {case.query_type}")


def _summary_text_for_case(case: BenchmarkCase, reference_data: dict[str, Any]) -> str:
    cache = reference_data["cache"]
    county_specific = cache["county_specific_summary"]
    all_summary = cache["all_jurisdiction_summary"]
    parts = [all_summary.get(f"{case.dataset}_analysis", "")]
    county = case.evidence.get("county")
    if county:
        parts.append(county_specific.get(county, ""))
    return "\n".join(part for part in parts if part).strip()


def _extract_names_from_summary(summary: str) -> list[str]:
    patterns = [
        r"Judge ([^.]+?) has the highest dismissal rate",
        r"Attorney ([^.]+?) has the highest win count",
        r"Attorney ([^.]+?) leads in jury trial wins",
    ]
    names = []
    for pattern in patterns:
        matches = re.findall(pattern, summary)
        names.extend(matches)
    return sorted({name.strip().upper() for name in names if name.strip()})


def _normalize_name_match(answer: list[str], candidates: list[str]) -> list[str]:
    if not candidates:
        return answer
    upper_candidates = {candidate.upper(): candidate for candidate in candidates}
    matched = []
    for item in answer:
        key = item.upper()
        if key in upper_candidates:
            matched.append(item)
            continue
        for candidate_upper in upper_candidates:
            if key in candidate_upper or candidate_upper in key:
                matched.append(upper_candidates[candidate_upper])
                break
    return sorted(set(matched)) or answer


def _offline_prompt_only(case: BenchmarkCase, reference_data: dict[str, Any], baseline_id: str) -> Prediction:
    answer, lookup_evidence = _lookup_answer(case, reference_data)
    summary_text = _summary_text_for_case(case, reference_data)
    summary_names = _extract_names_from_summary(summary_text)
    normalized = _normalize_name_match(answer, summary_names)
    context = _execution_context(baseline_id, mode="offline")
    return Prediction(
        case_id=case.case_id,
        runner=baseline_id,
        answer=normalized,
        evidence={
            **lookup_evidence,
            "mode": context.mode,
            "repo_path": context.repo_path,
            "notes": context.spec_notes,
            "summary_context_used": bool(summary_text),
            "summary_name_hints": summary_names,
        },
        latency_ms=0.0,
    )


def _run_real_wrapper(case: BenchmarkCase, baseline_id: str, wrapper_path: Path) -> Prediction:
    runtime = FRAMEWORK_RUNTIMES.get(baseline_id)
    if runtime is None:
        raise RuntimeError(f"No framework runtime is configured for baseline {baseline_id}.")

    if not runtime.python_path.exists():
        install_hint = (
            f"`python3 scripts/install_baseline_runtimes.py --baseline {baseline_id}`"
            if runtime.framework_id == "zeus"
            else "`python3 scripts/install_baseline_runtimes.py --all`"
        )
        raise RuntimeError(
            f"{baseline_id} requires {runtime.python_path}.\n"
            f"Install the repo-local framework runtime with {install_hint}."
        )
    spec = resolve_baseline(baseline_id)
    missing = missing_env_vars(spec)
    if missing:
        raise RuntimeError(
            f"{baseline_id} requires the following environment variables for live execution: "
            f"{', '.join(missing)}"
        )

    payload = {"baseline_id": baseline_id, "case": asdict(case)}
    env = os.environ.copy()
    if runtime.framework_id == "metagpt":
        config_dir = METAGPT_HOME / ".metagpt"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config2.yaml"
        config_path.write_text(
            '\n'.join(
                [
                    "llm:",
                    '  api_type: "openai"',
                    f'  model: "{env.get("METAGPT_MODEL", env.get("BENCHMARK_FRAMEWORK_MODEL", env.get("OPENAI_MODEL", "gpt-4o-mini")))}"',
                    f'  base_url: "{env.get("OPENAI_BASE_URL", "https://api.openai.com/v1")}"',
                    f'  api_key: "{env["OPENAI_API_KEY"]}"',
                ]
        )
            + "\n",
            encoding="utf-8",
        )
        env["HOME"] = str(METAGPT_HOME)
    if runtime.framework_id == "zeus":
        _seed_zeus_workflow_cache()
        gateway_base_url = _cloudflare_gateway_base_url_from_env(env)
        if gateway_base_url:
            env.setdefault("CLOUDFLARE_ZDR_AI_GATEWAY_BASE_URL", gateway_base_url)
        if env.get("OPENAI_API_KEY"):
            env.setdefault("CLOUDFLARE_ZDR_AI_GATEWAY_API_KEY", env["OPENAI_API_KEY"])
        env.setdefault("CACHE_URI", f"local://{LOCAL_WORKFLOW_CACHE_ROOT}")
        env.setdefault(
            "GP_BENCHMARK_COACTION_DATA_ROOT",
            str(ROOT / "cases" / "coaction_venue_risk" / "data"),
        )
        env.setdefault("GCLOUD_LOCAL_CREDENTIALS", "true")
    if runtime.framework_id == "metagpt":
        worker_key = (runtime.framework_id, str(wrapper_path))
        worker = _PERSISTENT_WRAPPERS.get(worker_key)
        if worker is None or worker.poll() is not None:
            worker = subprocess.Popen(
                [str(runtime.python_path), str(wrapper_path), "--server"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                cwd=ROOT,
                env=env,
                bufsize=1,
            )
            _PERSISTENT_WRAPPERS[worker_key] = worker
        assert worker.stdin is not None
        assert worker.stdout is not None
        worker.stdin.write(json.dumps(payload) + "\n")
        worker.stdin.flush()
        response = _read_persistent_wrapper_response(worker.stdout, baseline_id)
    else:
        try:
            completed = subprocess.run(
                [str(runtime.python_path), str(wrapper_path)],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=True,
                cwd=ROOT,
                env=env,
                timeout=_wrapper_timeout_seconds(runtime),
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"{baseline_id} real execution timed out after "
                f"{_wrapper_timeout_seconds(runtime):.0f}s."
            ) from exc
        except subprocess.CalledProcessError as exc:
            details = exc.stderr.strip() or exc.stdout.strip() or "no output"
            raise RuntimeError(f"{baseline_id} real execution failed: {details}") from exc

        response = _parse_wrapper_response(completed.stdout, baseline_id)

    answer = response.get("answer")
    if not isinstance(answer, list):
        raise RuntimeError(f"{baseline_id} returned an invalid answer payload: {response!r}")

    evidence = response.get("evidence")
    if not isinstance(evidence, dict):
        evidence = {}
    evidence.setdefault("mode", "framework_wrapper")
    evidence.setdefault("repo_path", _repo_path_for_baseline(baseline_id))
    evidence.setdefault("wrapper_path", str(wrapper_path))
    evidence.setdefault("framework_runtime", runtime.framework_id)

    latency_ms = response.get("latency_ms", 0.0)
    try:
        latency_value = float(latency_ms)
    except (TypeError, ValueError):
        latency_value = 0.0

    return Prediction(
        case_id=case.case_id,
        runner=baseline_id,
        answer=[str(item) for item in answer],
        evidence=evidence,
        latency_ms=latency_value,
    )


def _parse_wrapper_response(raw_text: str, baseline_id: str) -> dict[str, Any]:
    candidates = [raw_text.strip()]
    fenced_match = re.search(r"```(?:json|python)?\s*(\{.*\})\s*```", raw_text, flags=re.DOTALL)
    if fenced_match:
        candidates.insert(0, fenced_match.group(1).strip())
    object_match = re.search(r"(\{.*\})", raw_text, flags=re.DOTALL)
    if object_match:
        candidates.append(object_match.group(1).strip())

    for candidate in candidates:
        if not candidate:
            continue
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            try:
                payload = ast.literal_eval(candidate)
            except (ValueError, SyntaxError):
                continue
        if isinstance(payload, dict):
            return payload

    raise RuntimeError(
        f"{baseline_id} returned invalid JSON: {raw_text.strip() or 'empty output'}"
    )


def _read_persistent_wrapper_response(stdout: Any, baseline_id: str) -> dict[str, Any]:
    last_nonempty = ""
    for _ in range(200):
        raw_response = stdout.readline()
        if not raw_response:
            break
        if not raw_response.strip():
            continue
        last_nonempty = raw_response
        try:
            return _parse_wrapper_response(raw_response, baseline_id)
        except RuntimeError:
            continue
    raise RuntimeError(
        f"{baseline_id} real execution failed: wrapper exited unexpectedly or did not return parseable JSON. "
        f"Last output: {last_nonempty.strip() or 'empty output'}"
    )


def run_baseline_prediction(case: BenchmarkCase, reference_data: dict[str, Any], baseline_id: str) -> Prediction:
    spec = resolve_baseline(baseline_id)

    if baseline_id == "structured_lookup":
        answer, evidence = _lookup_answer(case, reference_data)
        return Prediction(
            case_id=case.case_id,
            runner=baseline_id,
            answer=answer,
            evidence=evidence,
            latency_ms=0.0,
        )

    if baseline_id == "openai_raw_llm":
        if not missing_env_vars(spec):
            model = configured_model_name(spec) or ""
            prediction = run_openai_raw_llm(case, model)
            prediction.evidence["mode"] = "live_api"
            return prediction
        return _offline_prompt_only(case, reference_data, baseline_id)

    if baseline_id == "openai_with_context":
        if not missing_env_vars(spec):
            model = configured_model_name(spec) or ""
            prediction = run_openai_with_context(case, model)
            prediction.evidence["mode"] = "live_api_with_context"
            return prediction
        return _offline_prompt_only(case, reference_data, baseline_id)

    if baseline_id == "anthropic_raw_llm":
        if not missing_env_vars(spec):
            model = configured_model_name(spec) or ""
            prediction = run_anthropic_raw_llm(case, model)
            prediction.evidence["mode"] = "live_api"
            return prediction
        return _offline_prompt_only(case, reference_data, baseline_id)

    if baseline_id == "anthropic_with_context":
        if not missing_env_vars(spec):
            model = configured_model_name(spec) or ""
            prediction = run_anthropic_with_context(case, model)
            prediction.evidence["mode"] = "live_api_with_context"
            return prediction
        return _offline_prompt_only(case, reference_data, baseline_id)

    if baseline_id == "react_agent":
        return _run_real_wrapper(case, baseline_id, AUTOGEN_REACT_WRAPPER)

    if baseline_id == "multi_agent_analyst_coder_critic":
        return _run_real_wrapper(case, baseline_id, METAGPT_WRAPPER)

    if baseline_id == "autogen_multi_agent":
        return _run_real_wrapper(case, baseline_id, AUTOGEN_MULTI_AGENT_WRAPPER)

    if baseline_id == "metagpt_sop_agent":
        return _run_real_wrapper(case, baseline_id, METAGPT_WRAPPER)

    if baseline_id == "single_agent_data_analyst":
        return _run_real_wrapper(case, baseline_id, LANGGRAPH_SINGLE_AGENT_WRAPPER)

    if baseline_id == "gp_zeus_venue_risk":
        return _run_real_wrapper(case, baseline_id, ZEUS_VENUE_RISK_WRAPPER)

    raise ValueError(f"Unsupported baseline: {baseline_id}")
