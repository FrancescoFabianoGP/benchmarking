# benchmarking

Benchmark harness workspace for GP workflow evaluation.

This repo is the coordination layer for benchmarking GP workflows and decision systems. It is meant to hold benchmark assets, evaluation harness code, runners, scoring, reports, and comparison workflows while pulling the main implementation repos in as Git submodules.

## Aim

The purpose of this repo is to give us one place to:

- define benchmark cases and datasets
- run comparable workflow arms against the same inputs
- score correctness, constraint adherence, evidence quality, reproducibility, latency, and cost
- compare GP systems against internal baselines and external-style baselines
- keep benchmark design material, reports, and execution artifacts close to the code that uses them

This repo is not the home of the core workflow engine or the reasoning engine itself.

- `GP_components/zeus-service` remains the workflow/orchestration layer
- `GP_components/reasoning-engine` remains the deterministic reasoning layer
- `benchmarking` is the harness and evaluation workspace around them

## Repo Contents

- `GP_components/reasoning-engine/`: Git submodule for deterministic reasoning and ontology-adjacent logic services
- `GP_components/zeus-service/`: Git submodule for workflows, orchestration, evaluation hooks, and execution metrics
- `documentation/`: benchmark design pack, comparison notes, API contract sketches, and planning materials

## Clone And Setup

Clone with submodules from the start:

```bash
git clone --recurse-submodules <benchmarking-repo-url>
```

If you already cloned without submodules:

```bash
git submodule update --init --recursive
```

This repo is configured to recurse into submodules on pull. After pulling, it is still a good habit to run:

```bash
git submodule update --init --recursive
```


## Environment Model

There is not yet a single top-level Python environment for `benchmarking`.

Right now the environment model is:

- `benchmarking` is the coordination repo
- each submodule keeps its own runtime and dependency setup
- benchmark harness code added here can either become its own package later or initially call into the submodules through scripts, APIs, or CLIs

That means environment setup is currently done per submodule.

## Reasoning Engine Environment

The reasoning engine submodule is a Python project managed with `uv`.

From inside `GP_components/reasoning-engine/`:

```bash
uv sync
```

Read the submodule README for project-specific details:

- [`GP_components/reasoning-engine/README.md`](GP_components/reasoning-engine/README.md)

## Zeus Service Environment

The Zeus submodule is also a Python project managed with `uv`, but it has a heavier runtime setup.

From inside `GP_components/zeus-service/`:

```bash
uv sync
```

Zeus also needs local and cloud configuration such as:

- Python 3.13+
- Docker or Rancher Desktop
- PostgreSQL for the LangGraph checkpoint store
- cloud credentials for GP development services
- `.env` values for API keys, Elastic, Auth0, Snowflake, and related services

Read the submodule README for the full setup:

- [`GP_components/zeus-service/README.md`](GP_components/zeus-service/README.md)

## Recommended First-Time Setup

1. Clone `benchmarking` with submodules.
2. Run `git submodule update --init --recursive`.
3. Set up `GP_components/reasoning-engine` with `uv sync`.
4. Set up `GP_components/zeus-service` with `uv sync` and its required `.env`, database, and cloud credentials.
5. Read the materials in `documentation/` before building the harness.

## Daily Use

Check submodule state:

```bash
git submodule status
```

Pull the workspace and keep submodules aligned:

```bash
git pull
git submodule update --init --recursive
```

## Benchmark Design Materials

The benchmark planning pack has been moved into:

- [`documentation/`](documentation)

Useful starting points:

- [`documentation/README.md`](documentation/README.md)
- [`documentation/BENCHMARK_DESIGN.md`](documentation/BENCHMARK_DESIGN.md)
- [`documentation/BASELINES.md`](documentation/BASELINES.md)
- [`documentation/EXTERNAL_BASELINE_REPOS.md`](documentation/EXTERNAL_BASELINE_REPOS.md)
- [`documentation/IMPLEMENTATION_PLAN.md`](documentation/IMPLEMENTATION_PLAN.md)
- [`documentation/API_CONTRACT.md`](documentation/API_CONTRACT.md)
- [`documentation/PUBLIC_BENCHMARKS.md`](documentation/PUBLIC_BENCHMARKS.md)

## Near-Term Structure

As this repo grows, the likely next structure is:

```text
documentation/
cases/
harness/
  runners/
  scoring/
  reports/
scripts/
GP_components/
  reasoning-engine/
  zeus-service/
```

This keeps benchmark logic separate from the implementation repos while still making it easy to run GP components side by side.

## Initial Working Draft

There is now a first thin benchmark loop built on top of the existing Coaction venue-risk data already checked into `GP_components/zeus-service`.

It currently:

- loads the existing UniCourt and Coaction local CSV tables
- generates a small factual benchmark case pack
- writes a baseline catalog covering deterministic, raw-LLM, and open-tooling comparator arms
- runs deterministic, raw-LLM, and agentic-wrapper baselines locally
- scores exact-match accuracy
- writes Markdown and JSON reports under `reports/`

Run it from the repo root with:

```bash
python3 scripts/run_initial_coaction_benchmark.py
```

Inspect the configured baseline ladder:

```bash
python3 scripts/run_initial_coaction_benchmark.py --list-baselines
```

Run the whole local suite:

```bash
python3 scripts/run_initial_coaction_benchmark.py --baseline all
```

Run the very basic benchmark entrypoint:

```bash
python3 scripts/run_basic_benchmark.py
```

Default outputs:

- `cases/coaction_venue_risk/initial_case_pack.json`
- `cases/coaction_venue_risk/baseline_catalog.json`
- `cases/coaction_venue_risk/external_repo_catalog.json`
- `cases/coaction_venue_risk/external_wrapper_manifest.json`
- `reports/coaction_initial_draft/scorecard.md`
- `reports/coaction_initial_draft/suite_scorecard.md`
- `reports/basic_benchmark/basic_benchmark.md`
- `reports/coaction_initial_draft/predictions.json`
- `reports/coaction_initial_draft/suite_predictions.json`
- `reports/coaction_initial_draft/scores.json`

This is intentionally still a thin slice on real local data. The next step is to replace offline wrappers and fallback modes with live provider APIs and real external-framework integrations where helpful.
