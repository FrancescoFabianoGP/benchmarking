# Very Basic Benchmark

This is the simplest benchmark pass across all currently registered approaches.

- Cases: `15`
- Data root: `/Users/fraano/Desktop/Repos/GP/benchmarking/cases/coaction_venue_risk/data`

## Approaches

| Baseline | Category | Status | Description |
|---|---|---|---|
| structured_lookup | deterministic_reference | ready | Reads the local benchmark tables directly and returns exact answers. |

## Results

| Baseline | Accuracy | Avg Latency (ms) | Tokens | Est. Cost (USD) |
|---|---:|---:|---:|---:|
| structured_lookup | 100.0% | 0.03 | n/a | n/a |

## Notes

- This is still a thin factual benchmark over local venue-risk data.
- GPT and Claude baselines use offline fallback behavior until API keys are configured.
- The LangGraph, AutoGen, and MetaGPT baselines run through real framework wrappers after `python3 scripts/install_baseline_runtimes.py --all`.
