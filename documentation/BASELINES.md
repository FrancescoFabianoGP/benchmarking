# Baseline Plan

This repo now has a baseline registry wired into a benchmark registry, with the current thin Coaction benchmark as the first registered benchmark.

## Baselines Added

The current baseline catalog follows the comparison ladder already sketched in the planning docs and the resources listed in `documentation/GP_relevant_res.xlsx`.

We now also keep a small set of cloned external repositories under `baselines/` and describe their wrapper plans in [`documentation/EXTERNAL_BASELINE_REPOS.md`](EXTERNAL_BASELINE_REPOS.md).

Included now:

- `structured_lookup`: deterministic reference baseline over the local Coaction and UniCourt tables.
- `openai_raw_llm`: plain GPT baseline with offline fallback until API credentials are configured.
- `anthropic_raw_llm`: plain Claude baseline with offline fallback until API credentials are configured.
- `gp_zeus_venue_risk`: real Zeus venue-risk workflow baseline over the current Coaction benchmark.
- `react_agent`: live AutoGen ReAct-style baseline over benchmark-safe local data tools.
- `multi_agent_analyst_coder_critic`: live MetaGPT multi-role baseline aligned with the spreadsheet's multi-agent baseline note.
- `autogen_multi_agent`: live AutoGen collaboration baseline using a multi-agent team over local data tools.
- `metagpt_sop_agent`: live MetaGPT Data Interpreter baseline over benchmark-safe local data tools.
- `single_agent_data_analyst`: live LangGraph single-agent baseline inspired by DABStep, DAEval, and FDABench.

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
- `gp_zeus_venue_risk`
- `react_agent`
- `multi_agent_analyst_coder_critic`
- `autogen_multi_agent`
- `metagpt_sop_agent`
- `single_agent_data_analyst`

All of the above are wired into the local benchmark loop.

For `openai_raw_llm` and `anthropic_raw_llm`:

- without API keys they run in offline fallback mode
- once keys are added they can call the live provider APIs instead

For `react_agent`, `autogen_multi_agent`, `metagpt_sop_agent`, `multi_agent_analyst_coder_critic`, and `single_agent_data_analyst`:

- they now require `OPENAI_API_KEY`
- they use live model-backed framework execution instead of replay/no-op/deterministic wrapper logic

For `gp_zeus_venue_risk`:

- it requires the repo-local Zeus runtime under `.baseline_envs/zeus`
- it executes the real Zeus venue-risk workflow from `GP_components/zeus-service`
- the benchmark harness auto-points Zeus at `cases/coaction_venue_risk/data`
- the benchmark harness auto-configures a repo-local workflow cache for this benchmark path
- it primarily needs live LLM credentials via either `OPENAI_API_KEY` plus `OPENAI_BASE_URL`, or the equivalent `CLOUDFLARE_ZDR_AI_GATEWAY_*` env vars

## Environment Variables

For OpenAI:

- `OPENAI_API_KEY`
- optional `OPENAI_MODEL`
- optional `OPENAI_BASE_URL`
- optional `BENCHMARK_FRAMEWORK_MODEL`
- optional per-framework overrides such as `AUTOGEN_REACT_MODEL`, `AUTOGEN_MULTI_AGENT_MODEL`, `LANGGRAPH_MODEL`, `METAGPT_MODEL`

For Anthropic:

- `ANTHROPIC_API_KEY`
- optional `ANTHROPIC_MODEL`

For Zeus:

- `OPENAI_API_KEY` or `CLOUDFLARE_ZDR_AI_GATEWAY_API_KEY`
- `OPENAI_BASE_URL` or `CLOUDFLARE_ZDR_AI_GATEWAY_BASE_URL`
- optional `CACHE_URI`
- optional `GP_BENCHMARK_COACTION_DATA_ROOT`
- optional `GCLOUD_LOCAL_CREDENTIALS`

## Useful Commands

List the baseline catalog:

```bash
python3 scripts/run_initial_coaction_benchmark.py --list-baselines
```

Or through the generic entrypoint:

```bash
python3 scripts/run_benchmark.py --list-baselines
```

Run the deterministic reference baseline:

```bash
python3 scripts/run_initial_coaction_benchmark.py --baseline structured_lookup
```

Or:

```bash
python3 scripts/run_benchmark.py --benchmark coaction_venue_risk --baseline structured_lookup
```

Run the whole suite:

```bash
python3 scripts/run_initial_coaction_benchmark.py --baseline all
```

Or:

```bash
python3 scripts/run_benchmark.py --benchmark coaction_venue_risk --baseline all
```

Install the Zeus runtime:

```bash
python3 scripts/install_baseline_runtimes.py --baseline gp_zeus_venue_risk
```

Run only the Zeus baseline:

```bash
python3 scripts/run_benchmark.py --benchmark coaction_venue_risk --baseline gp_zeus_venue_risk
```

Run the plain GPT baseline once credentials are configured:

```bash
OPENAI_API_KEY=... OPENAI_MODEL=... python3 scripts/run_initial_coaction_benchmark.py --baseline openai_raw_llm
```

Run the plain Claude baseline once credentials are configured:

```bash
ANTHROPIC_API_KEY=... ANTHROPIC_MODEL=... python3 scripts/run_initial_coaction_benchmark.py --baseline anthropic_raw_llm
```
