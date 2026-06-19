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

- `zeus-service` remains the workflow/orchestration layer
- `reasoning-engine` remains the deterministic reasoning layer
- `benchmarking` is the harness and evaluation workspace around them

## Repo Contents

- `reasoning-engine/`: Git submodule for deterministic reasoning and ontology-adjacent logic services
- `zeus-service/`: Git submodule for workflows, orchestration, evaluation hooks, and execution metrics
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

## SSH Setup

This workspace is easiest to use if GP repos point at the GP SSH host alias.

Example `~/.ssh/config`:

```sshconfig
Host github-gp
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_GPkey
  IdentitiesOnly yes
  AddKeysToAgent yes
  UseKeychain yes
```

Then GP remotes should look like:

```bash
git@github-gp:growth-protocol-ai/reasoning-engine.git
git@github-gp:growth-protocol-ai/zeus-service.git
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

From inside `reasoning-engine/`:

```bash
uv sync
```

Read the submodule README for project-specific details:

- [`reasoning-engine/README.md`](reasoning-engine/README.md)

## Zeus Service Environment

The Zeus submodule is also a Python project managed with `uv`, but it has a heavier runtime setup.

From inside `zeus-service/`:

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

- [`zeus-service/README.md`](zeus-service/README.md)

## Recommended First-Time Setup

1. Clone `benchmarking` with submodules.
2. Run `git submodule update --init --recursive`.
3. Verify both submodules use the GP SSH alias if they are GP-owned repos.
4. Set up `reasoning-engine` with `uv sync`.
5. Set up `zeus-service` with `uv sync` and its required `.env`, database, and cloud credentials.
6. Read the materials in `documentation/` before building the harness.

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
reasoning-engine/
zeus-service/
```

This keeps benchmark logic separate from the implementation repos while still making it easy to run GP components side by side.
