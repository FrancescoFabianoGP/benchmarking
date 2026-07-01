# Coaction Benchmark Share Sheet

This is the short benchmark index to send around.

## What This Benchmark Tests

Benchmark:

- [cases/coaction_venue_risk/benchmark_manifest.json](/Users/fraano/Desktop/Repos/GP/benchmarking/cases/coaction_venue_risk/benchmark_manifest.json)

Question set:

- [cases/coaction_venue_risk/initial_case_pack.json](/Users/fraano/Desktop/Repos/GP/benchmarking/cases/coaction_venue_risk/initial_case_pack.json)

Current question families:

- `county_metric_extreme`: county winners over overall court statistics
- `county_top_judge_dismissal_rate`: top judge within a county over judge dismissal tables

Datasets:

- `unicourt`
- `coaction`

## Benchmark Context

Table bundle:

- [cases/coaction_venue_risk/data/unicourt_tables](/Users/fraano/Desktop/Repos/GP/benchmarking/cases/coaction_venue_risk/data/unicourt_tables)
- [cases/coaction_venue_risk/data/coaction_tables](/Users/fraano/Desktop/Repos/GP/benchmarking/cases/coaction_venue_risk/data/coaction_tables)

Cached summaries:

- [cases/coaction_venue_risk/data/cache](/Users/fraano/Desktop/Repos/GP/benchmarking/cases/coaction_venue_risk/data/cache)

Parsing metadata:

- [cases/coaction_venue_risk/parsing/manifest.json](/Users/fraano/Desktop/Repos/GP/benchmarking/cases/coaction_venue_risk/parsing/manifest.json)

## Baselines

Baseline catalog:

- [cases/coaction_venue_risk/baseline_catalog.json](/Users/fraano/Desktop/Repos/GP/benchmarking/cases/coaction_venue_risk/baseline_catalog.json)

Current methods:

- `structured_lookup`
- `openai_raw_llm`
- `openai_with_context`
- `anthropic_raw_llm`
- `anthropic_with_context`
- `react_agent`
- `multi_agent_analyst_coder_critic`
- `autogen_multi_agent`
- `metagpt_sop_agent`
- `single_agent_data_analyst`
- `gp_zeus_venue_risk`

Paper links for applicable methods are shown directly in:

- [reports/runs/coaction_all_baselines_gpt55/suite_status.md](/Users/fraano/Desktop/Repos/GP/benchmarking/reports/runs/coaction_all_baselines_gpt55/suite_status.md)

## Metrics

Metric implementation:

- [harness/scoring.py](/Users/fraano/Desktop/Repos/GP/benchmarking/harness/scoring.py)

Current reported metrics:

- overall exact-match accuracy
- accuracy by dataset
- accuracy by query type
- average latency
- average wall time
- average CPU time
- average I/O wait
- total wall time
- total CPU time
- total I/O wait
- token totals when available
- estimated cost when available

## Current Results

Suite summary:

- [reports/runs/coaction_all_baselines_gpt55/suite_status.md](/Users/fraano/Desktop/Repos/GP/benchmarking/reports/runs/coaction_all_baselines_gpt55/suite_status.md)

GP-specific comparison:

- [reports/runs/coaction_all_baselines_gpt55/gp_workflow_analysis.md](/Users/fraano/Desktop/Repos/GP/benchmarking/reports/runs/coaction_all_baselines_gpt55/gp_workflow_analysis.md)

Note:

- the GP comparison excludes `structured_lookup`, so GP is compared only against non-reference baselines

## Useful Commands

Run one baseline:

```bash
python3 scripts/run_benchmark.py --benchmark coaction_venue_risk --baseline openai_with_context
```

Run the full suite:

```bash
python3 scripts/run_coaction_all_baselines_gpt55.sh
```
