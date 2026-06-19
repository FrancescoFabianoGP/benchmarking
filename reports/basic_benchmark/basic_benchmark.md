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
| react_agent | open_tooling | offline_ready | Open agent baseline with thought-action-observation loops and tool calls. |
| multi_agent_analyst_coder_critic | open_tooling | offline_ready | Specialized multi-agent workflow baseline for analysis and self-critique. |
| autogen_multi_agent | agentic_architecture | offline_ready | Conversational multi-agent architecture baseline for collaborative data-analysis workflows. |
| metagpt_sop_agent | agentic_architecture | offline_ready | Multi-agent SOP-style architecture baseline emphasizing role separation and staged execution. |
| single_agent_data_analyst | agentic_architecture | offline_ready | Single open data agent baseline over heterogeneous files and analytical questions. |

## Results

| Baseline | Accuracy | Avg Latency (ms) |
|---|---:|---:|
| structured_lookup | 100.0% | 0.04 |
| openai_raw_llm | 100.0% | 0.21 |
| anthropic_raw_llm | 100.0% | 0.17 |
| react_agent | 100.0% | 0.15 |
| multi_agent_analyst_coder_critic | 100.0% | 0.13 |
| autogen_multi_agent | 100.0% | 0.11 |
| metagpt_sop_agent | 100.0% | 0.11 |
| single_agent_data_analyst | 100.0% | 0.12 |

## Notes

- This is still a thin factual benchmark over local venue-risk data.
- GPT and Claude baselines use offline fallback behavior until API keys are configured.
- Agentic baselines currently run through local wrapper logic, not full upstream framework execution.
