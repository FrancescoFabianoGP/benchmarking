# External Baseline Repos

The benchmark repo now vendors a small set of external baseline repositories under `baselines/`.

Current clones:

- `baselines/metagpt`
- `baselines/autogen`
- `baselines/langgraph`

## Why These Repos

They cover the agentic architecture families we agreed were acceptable comparison points:

- SOP-style multi-agent workflows
- named multi-agent orchestration frameworks
- single-agent data-analysis architectures

## Wrapper Strategy

We are not trying to run the full upstream products as-is.

Instead, we run narrow framework-backed wrappers that:

- take one benchmark case as input
- expose a normalized output schema
- limit tool/file access to benchmark assets
- make latency and trace capture comparable across baselines

Current working wrappers:

- `harness/framework_runners/langgraph_single_agent.py`
- `harness/framework_runners/autogen_react_agent.py`
- `harness/framework_runners/autogen_multi_agent.py`
- `harness/framework_runners/metagpt_wrappers.py`

Generated manifests:

- `cases/coaction_venue_risk/external_repo_catalog.json`
- `cases/coaction_venue_risk/external_wrapper_manifest.json`

Generate or refresh them with:

```bash
python3 scripts/generate_external_baseline_catalog.py
```

Install the repo-local framework runtimes with:

```bash
python3 scripts/install_baseline_runtimes.py --all
```

## Runtime Setup

Install every repo-local baseline runtime with:

```bash
python3 scripts/install_baseline_runtimes.py --all
```

That script creates reproducible virtual environments under `.baseline_envs/` from the vendored baseline repos, so a fresh checkout can enable all framework-backed baselines in one step.

The live framework runs also require `OPENAI_API_KEY`, and optionally:

- `OPENAI_BASE_URL`
- `BENCHMARK_FRAMEWORK_MODEL`
- `AUTOGEN_REACT_MODEL`
- `AUTOGEN_MULTI_AGENT_MODEL`
- `LANGGRAPH_MODEL`
- `METAGPT_MODEL`
