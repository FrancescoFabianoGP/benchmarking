# Baselines

This repo keeps a single baseline registry and uses it across benchmark execution, reporting, and method summaries.

The active registry lives in:

- [harness/baseline_registry.py](/Users/fraano/Desktop/Repos/GP/benchmarking/harness/baseline_registry.py)
- [cases/coaction_venue_risk/baseline_catalog.json](/Users/fraano/Desktop/Repos/GP/benchmarking/cases/coaction_venue_risk/baseline_catalog.json)

## Baseline Ladder

The current Coaction suite includes:

- `structured_lookup`: deterministic reference over the benchmark-local tables
- `openai_raw_llm`: prompt-only OpenAI baseline
- `openai_with_context`: OpenAI baseline with relevant local tables and summaries in context
- `anthropic_raw_llm`: prompt-only Anthropic baseline
- `anthropic_with_context`: Anthropic baseline with relevant local tables and summaries in context
- `react_agent`: ReAct-style tool-using baseline
- `multi_agent_analyst_coder_critic`: multi-agent analyst/coder/critic baseline
- `autogen_multi_agent`: AutoGen-style collaborative multi-agent baseline
- `metagpt_sop_agent`: MetaGPT-style SOP baseline
- `single_agent_data_analyst`: single-agent data-analysis baseline
- `gp_zeus_venue_risk`: the real GP Zeus venue-risk workflow

## Runtime Model

Raw API baselines:

- `openai_raw_llm`
- `openai_with_context`
- `anthropic_raw_llm`
- `anthropic_with_context`

Framework baselines that use repo-local runtimes under `.baseline_envs/`:

- `react_agent`
- `multi_agent_analyst_coder_critic`
- `autogen_multi_agent`
- `metagpt_sop_agent`
- `single_agent_data_analyst`
- `gp_zeus_venue_risk`

Install the local framework runtimes with:

```bash
python3 scripts/install_baseline_runtimes.py --all
```

Install only the Zeus runtime with:

```bash
python3 scripts/install_baseline_runtimes.py --baseline gp_zeus_venue_risk
```

## Environment Variables

Common OpenAI-style settings:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_MODEL`
- `BENCHMARK_FRAMEWORK_MODEL`

Framework-specific optional overrides:

- `AUTOGEN_REACT_MODEL`
- `AUTOGEN_MULTI_AGENT_MODEL`
- `LANGGRAPH_MODEL`
- `METAGPT_MODEL`
- `METAGPT_COMPAT_MODEL`

Anthropic settings:

- `ANTHROPIC_API_KEY`
- `ANTHROPIC_BASE_URL`
- `ANTHROPIC_MODEL`

Keep local secrets in `.env`:

```bash
cp .env.example .env
```

## Paper Links

The method-summary paper links shown in the suite report are derived from:

- [documentation/GP_relevant_res.xlsx](/Users/fraano/Desktop/Repos/GP/benchmarking/documentation/GP_relevant_res.xlsx)

Those links are surfaced into:

- [reports/runs/coaction_all_baselines_gpt55/suite_status.md](/Users/fraano/Desktop/Repos/GP/benchmarking/reports/runs/coaction_all_baselines_gpt55/suite_status.md)

## Report References

Current aggregate outputs:

- [reports/runs/coaction_all_baselines_gpt55/suite_status.md](/Users/fraano/Desktop/Repos/GP/benchmarking/reports/runs/coaction_all_baselines_gpt55/suite_status.md)
- [reports/runs/coaction_all_baselines_gpt55/gp_workflow_analysis.md](/Users/fraano/Desktop/Repos/GP/benchmarking/reports/runs/coaction_all_baselines_gpt55/gp_workflow_analysis.md)

The GP comparative report intentionally excludes `structured_lookup` from the GP-vs-others comparison, so GP is measured against live non-reference baselines rather than the deterministic oracle.
