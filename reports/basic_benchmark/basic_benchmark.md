# Very Basic Benchmark

This is the simplest benchmark pass across all currently registered approaches.

- Cases: `15`
- Data root: `/Users/fraano/Desktop/Repos/GP/benchmarking/GP_components/zeus-service/app/workflow/local_db/coaction`

## Approaches

| Baseline | Category | Status | Description |
|---|---|---|---|
| structured_lookup | deterministic_reference | ready | Reads the local benchmark tables directly and returns exact answers. |
| openai_raw_llm | llm_only | offline_ready_live_if_configured | Prompt-only GPT baseline over the same case question and output schema. |
| anthropic_raw_llm | llm_only | offline_ready_live_if_configured | Prompt-only Claude baseline over the same case question and output schema. |
| react_agent | open_tooling | framework_wrapper_requires_runtime | Open agent baseline with thought-action-observation loops and tool calls. |
| multi_agent_analyst_coder_critic | open_tooling | framework_wrapper_requires_runtime | Specialized multi-agent workflow baseline for analysis and self-critique. |
| autogen_multi_agent | agentic_architecture | framework_wrapper_requires_runtime | Conversational multi-agent architecture baseline for collaborative data-analysis workflows. |
| metagpt_sop_agent | agentic_architecture | framework_wrapper_requires_runtime | Multi-agent SOP-style architecture baseline emphasizing role separation and staged execution. |
| single_agent_data_analyst | agentic_architecture | framework_wrapper_requires_runtime | Single open data agent baseline over heterogeneous files and analytical questions. |

## Results

| Baseline | Accuracy | Avg Latency (ms) |
|---|---:|---:|
| structured_lookup | 100.0% | 0.02 |
| openai_raw_llm | 100.0% | 0.12 |
| anthropic_raw_llm | 100.0% | 0.11 |
| react_agent | 100.0% | 2.52 |
| multi_agent_analyst_coder_critic | 100.0% | 117.98 |
| autogen_multi_agent | 100.0% | 3.47 |
| metagpt_sop_agent | 100.0% | 69.11 |
| single_agent_data_analyst | 100.0% | 5.59 |

## Notes

- This is still a thin factual benchmark over local venue-risk data.
- GPT and Claude baselines use offline fallback behavior until API keys are configured.
- The LangGraph, AutoGen, and MetaGPT baselines run through real framework wrappers after `python3 scripts/install_baseline_runtimes.py --all`.
