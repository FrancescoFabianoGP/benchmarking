# GP Benchmarking

This repo is the benchmark harness around GP workflows and comparison baselines.

It is where we:

- define benchmark cases and benchmark-local data bundles
- run GP and non-GP baselines against the same prompts
- score accuracy, latency, CPU time, I/O wait, token usage, and estimated cost
- generate benchmark reports and side-by-side comparisons

The core workflow systems still live in submodules:

- `GP_components/zeus-service`
- `GP_components/reasoning-engine`

## Quick Start

Clone with submodules:

```bash
git clone --recurse-submodules <repo-url>
cd benchmarking
```

If needed later:

```bash
git submodule update --init --recursive
```

Create local env vars:

```bash
cp .env.example .env
```

Install the local framework runtimes used by the live baselines:

```bash
python3 scripts/install_baseline_runtimes.py --all
```

Sync the benchmark-local Coaction data bundle:

```bash
python3 scripts/sync_benchmark_assets.py --benchmark coaction_venue_risk
```

## Main Benchmark

The current primary benchmark is `coaction_venue_risk`.

Useful commands:

```bash
python3 scripts/run_benchmark.py --list-benchmarks
python3 scripts/run_benchmark.py --list-baselines
python3 scripts/run_benchmark.py --benchmark coaction_venue_risk --baseline structured_lookup
python3 scripts/run_benchmark.py --benchmark coaction_venue_risk --baseline openai_with_context
python3 scripts/run_coaction_all_baselines_gpt55.sh
```

The benchmark-local assets live under:

- [cases/coaction_venue_risk/README.md](/Users/fraano/Desktop/Repos/GP/benchmarking/cases/coaction_venue_risk/README.md)
- [cases/coaction_venue_risk/benchmark_manifest.json](/Users/fraano/Desktop/Repos/GP/benchmarking/cases/coaction_venue_risk/benchmark_manifest.json)
- [cases/coaction_venue_risk/initial_case_pack.json](/Users/fraano/Desktop/Repos/GP/benchmarking/cases/coaction_venue_risk/initial_case_pack.json)

## Reports

The current full-suite run is:

- [reports/runs/coaction_all_baselines_gpt55/suite_status.md](/Users/fraano/Desktop/Repos/GP/benchmarking/reports/runs/coaction_all_baselines_gpt55/suite_status.md)
- [reports/runs/coaction_all_baselines_gpt55/gp_workflow_analysis.md](/Users/fraano/Desktop/Repos/GP/benchmarking/reports/runs/coaction_all_baselines_gpt55/gp_workflow_analysis.md)

Each per-baseline folder contains:

- `predictions.json`
- `scores.json`
- `scorecard.md`
- `suite_scorecard.md`

## Documentation

Start here:

- [documentation/README.md](/Users/fraano/Desktop/Repos/GP/benchmarking/documentation/README.md)
- [documentation/COACTION_BENCHMARK_SHARE.md](/Users/fraano/Desktop/Repos/GP/benchmarking/documentation/COACTION_BENCHMARK_SHARE.md)
- [documentation/BASELINES.md](/Users/fraano/Desktop/Repos/GP/benchmarking/documentation/BASELINES.md)
- [documentation/BENCHMARK_DESIGN.md](/Users/fraano/Desktop/Repos/GP/benchmarking/documentation/BENCHMARK_DESIGN.md)

## Notes

- `.env` is ignored, so local API keys stay uncommitted.
- `.baseline_envs/` and `.benchmark_cache/` are local-only runtime directories.
- `reports/runs/` is treated as generated output rather than committed source.
