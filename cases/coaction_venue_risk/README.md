# Coaction Venue Risk Benchmark

This folder is the benchmark-local package for the current Coaction venue-risk evaluation.

## What It Contains

- [benchmark_manifest.json](/Users/fraano/Desktop/Repos/GP/benchmarking/cases/coaction_venue_risk/benchmark_manifest.json): benchmark metadata, dataset layout, and source roots
- [initial_case_pack.json](/Users/fraano/Desktop/Repos/GP/benchmarking/cases/coaction_venue_risk/initial_case_pack.json): the 15 benchmark questions with gold answers
- [baseline_catalog.json](/Users/fraano/Desktop/Repos/GP/benchmarking/cases/coaction_venue_risk/baseline_catalog.json): current baseline snapshot
- [external_repo_catalog.json](/Users/fraano/Desktop/Repos/GP/benchmarking/cases/coaction_venue_risk/external_repo_catalog.json): external baseline repo metadata
- [external_wrapper_manifest.json](/Users/fraano/Desktop/Repos/GP/benchmarking/cases/coaction_venue_risk/external_wrapper_manifest.json): wrapper entrypoints used by the harness
- [parsing/manifest.json](/Users/fraano/Desktop/Repos/GP/benchmarking/cases/coaction_venue_risk/parsing/manifest.json): parsing metadata for the copied tables

## Data Bundle

The benchmark uses benchmark-local copies of the source material under:

- [data/unicourt_tables](/Users/fraano/Desktop/Repos/GP/benchmarking/cases/coaction_venue_risk/data/unicourt_tables)
- [data/coaction_tables](/Users/fraano/Desktop/Repos/GP/benchmarking/cases/coaction_venue_risk/data/coaction_tables)
- [data/cache](/Users/fraano/Desktop/Repos/GP/benchmarking/cases/coaction_venue_risk/data/cache)

The upstream source is still the Zeus local DB bundle:

- `GP_components/zeus-service/app/workflow/local_db/coaction`

Refresh the benchmark-local copy with:

```bash
python3 scripts/sync_benchmark_assets.py --benchmark coaction_venue_risk
```

## Question Shape

The current case pack has 15 questions:

- 10 `county_metric_extreme` questions over county-level court metrics
- 5 `county_top_judge_dismissal_rate` questions over county-level judge dismissal rates

Datasets:

- `unicourt`
- `coaction`

To inspect the exact questions:

```bash
python3 - <<'PY'
import json
from pathlib import Path
cases = json.loads(Path('cases/coaction_venue_risk/initial_case_pack.json').read_text())
for case in cases:
    print(case['case_id'], '|', case['dataset'], '|', case['query_type'], '|', case['prompt'])
PY
```

## Main Commands

Run one baseline:

```bash
python3 scripts/run_benchmark.py --benchmark coaction_venue_risk --baseline structured_lookup
```

Run all registered baselines:

```bash
python3 scripts/run_coaction_all_baselines_gpt55.sh
```

List baselines:

```bash
python3 scripts/run_benchmark.py --list-baselines
```

## Metrics

The harness currently reports:

- exact-match accuracy
- accuracy by dataset
- accuracy by query type
- average and total latency
- average and total wall time
- average and total CPU time
- average and total I/O wait
- token totals when available
- estimated cost when available

Metric aggregation lives in [harness/scoring.py](/Users/fraano/Desktop/Repos/GP/benchmarking/harness/scoring.py).

## Current Report Set

The main report folder is:

- [reports/runs/coaction_all_baselines_gpt55](/Users/fraano/Desktop/Repos/GP/benchmarking/reports/runs/coaction_all_baselines_gpt55)

Most useful summary files:

- [suite_status.md](/Users/fraano/Desktop/Repos/GP/benchmarking/reports/runs/coaction_all_baselines_gpt55/suite_status.md)
- [gp_workflow_analysis.md](/Users/fraano/Desktop/Repos/GP/benchmarking/reports/runs/coaction_all_baselines_gpt55/gp_workflow_analysis.md)
