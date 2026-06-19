# Baseline Plan

This repo now has a first baseline registry wired into the thin Coaction benchmark harness.

## Baselines Added

The current baseline catalog follows the comparison ladder already sketched in the planning docs and the resources listed in `documentation/GP_relevant_res.xlsx`.

We now also keep a small set of cloned external repositories under `baselines/` and describe their wrapper plans in [`documentation/EXTERNAL_BASELINE_REPOS.md`](EXTERNAL_BASELINE_REPOS.md).

Included now:

- `structured_lookup`: deterministic reference baseline over the local Coaction and UniCourt tables.
- `openai_raw_llm`: plain GPT baseline with offline fallback until API credentials are configured.
- `anthropic_raw_llm`: plain Claude baseline with offline fallback until API credentials are configured.
- `react_agent`: open-tooling baseline aligned with the ReAct paper and spreadsheet note.
- `multi_agent_analyst_coder_critic`: open-tooling baseline aligned with the spreadsheet's multi-agent baseline note and AutoGen-style workflows.
- `autogen_multi_agent`: agentic-architecture baseline using an AutoGen-style collaboration pattern.
- `metagpt_sop_agent`: agentic-architecture baseline using a MetaGPT-style SOP pattern.
- `single_agent_data_analyst`: agentic-architecture baseline inspired by DABStep, DAEval, and FDABench.

## Why These Baselines

The spreadsheet explicitly calls out three especially relevant comparison points:

- `LLM-only analyst`
- `ReAct agent`
- `Multi-agent analyst/coder/critic workflow`

It also points to agentic-architecture families that are worth tracking as named baselines:

- `AutoGen`
- `MetaGPT`
- `DABStep / DAEval / FDABench` style data agents

That maps well to the benchmark positioning docs:

- raw LLM
- LLM plus open agent tooling
- GP governed stack

## Current Status

What runs today:

- `structured_lookup`
- `openai_raw_llm`
- `anthropic_raw_llm`
- `react_agent`
- `multi_agent_analyst_coder_critic`
- `autogen_multi_agent`
- `metagpt_sop_agent`
- `single_agent_data_analyst`

All of the above run now in the local benchmark loop.

For `openai_raw_llm` and `anthropic_raw_llm`:

- without API keys they run in offline fallback mode
- once keys are added they can call the live provider APIs instead

## Environment Variables

For OpenAI:

- `OPENAI_API_KEY`
- optional `OPENAI_MODEL`

For Anthropic:

- `ANTHROPIC_API_KEY`
- optional `ANTHROPIC_MODEL`

## Useful Commands

List the baseline catalog:

```bash
python3 scripts/run_initial_coaction_benchmark.py --list-baselines
```

Run the deterministic reference baseline:

```bash
python3 scripts/run_initial_coaction_benchmark.py --baseline structured_lookup
```

Run the whole suite:

```bash
python3 scripts/run_initial_coaction_benchmark.py --baseline all
```

Run the plain GPT baseline once credentials are configured:

```bash
OPENAI_API_KEY=... OPENAI_MODEL=... python3 scripts/run_initial_coaction_benchmark.py --baseline openai_raw_llm
```

Run the plain Claude baseline once credentials are configured:

```bash
ANTHROPIC_API_KEY=... ANTHROPIC_MODEL=... python3 scripts/run_initial_coaction_benchmark.py --baseline anthropic_raw_llm
```
