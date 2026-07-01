# Coaction Venue Risk Benchmark

This benchmark folder is the self-contained home for the Coaction venue-risk benchmark.

## Layout

- `data/`: benchmark-local copies of the CSV tables and cached summaries used by the benchmark
- `parsing/`: metadata about how the benchmark source data is parsed upstream and in the harness
- `initial_case_pack.json`: generated benchmark cases
- `baseline_catalog.json`: registered baseline catalog snapshot
- `external_repo_catalog.json`: external baseline repo catalog snapshot
- `external_wrapper_manifest.json`: wrapper entrypoints for external baselines

## Data Source

The current source of truth for this benchmark's raw inputs comes from:

- `GP_components/zeus-service/app/workflow/local_db/coaction/`

Sync the tracked source data into this folder with:

```bash
python3 scripts/sync_benchmark_assets.py --benchmark coaction_venue_risk
```

The harness prefers `cases/coaction_venue_risk/data/` and falls back to the legacy Zeus path only if the benchmark-local copy does not exist.
