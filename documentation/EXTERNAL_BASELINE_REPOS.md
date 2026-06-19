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

Instead, the plan is to build narrow wrappers that:

- take one benchmark case as input
- expose a normalized output schema
- limit tool/file access to benchmark assets
- make latency and trace capture comparable across baselines

Generated manifests:

- `cases/coaction_venue_risk/external_repo_catalog.json`
- `cases/coaction_venue_risk/external_wrapper_manifest.json`

Generate or refresh them with:

```bash
python3 scripts/generate_external_baseline_catalog.py
```

## Recommended First Wrapper

Start with `single_agent_data_analyst` on top of `LangGraph`.

That is the lightest useful architecture baseline because it lets us build a very small graph around:

- local file loading
- analysis
- answer formatting

without inheriting the full complexity of MetaGPT or AutoGen on day one.
