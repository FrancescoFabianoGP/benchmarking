#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="${1:-reports/runs/coaction_all_baselines_gpt55}"
LOG_DIR="$REPORT_DIR"
LOG_FILE="$LOG_DIR/run.log"
START_TS="$(date +%s)"

cd "$ROOT_DIR"

mkdir -p "$LOG_DIR"

timestamp() {
  date +"%Y-%m-%d %H:%M:%S"
}

log() {
  echo "[$(timestamp)] [coaction-suite] $*"
}

run_logged() {
  log "command: $*"
  "$@"
}

log "repo: $ROOT_DIR"
log "report dir: $REPORT_DIR"
log "log file: $LOG_FILE"

if [[ -f .env ]]; then
  log "loading .env"
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
else
  log "no .env found, using current shell environment"
fi

export OPENAI_MODEL="${OPENAI_MODEL:-gpt-5.5}"
export BENCHMARK_FRAMEWORK_MODEL="${BENCHMARK_FRAMEWORK_MODEL:-gpt-5.5}"
export AUTOGEN_REACT_MODEL="${AUTOGEN_REACT_MODEL:-gpt-5.5}"
export AUTOGEN_MULTI_AGENT_MODEL="${AUTOGEN_MULTI_AGENT_MODEL:-gpt-5.5}"
export LANGGRAPH_MODEL="${LANGGRAPH_MODEL:-gpt-5.5}"
export METAGPT_MODEL="${METAGPT_MODEL:-gpt-4o-mini}"
export METAGPT_COMPAT_MODEL="${METAGPT_COMPAT_MODEL:-gpt-4o-mini}"
export MAX_PARALLEL_BASELINES="${MAX_PARALLEL_BASELINES:-0}"
export SUITE_PROGRESS_INTERVAL_SECONDS="${SUITE_PROGRESS_INTERVAL_SECONDS:-5}"
export PYTHONUNBUFFERED=1

log "OPENAI_MODEL=$OPENAI_MODEL"
log "BENCHMARK_FRAMEWORK_MODEL=$BENCHMARK_FRAMEWORK_MODEL"
log "AUTOGEN_REACT_MODEL=$AUTOGEN_REACT_MODEL"
log "AUTOGEN_MULTI_AGENT_MODEL=$AUTOGEN_MULTI_AGENT_MODEL"
log "LANGGRAPH_MODEL=$LANGGRAPH_MODEL"
log "METAGPT_MODEL=$METAGPT_MODEL"
log "METAGPT_COMPAT_MODEL=$METAGPT_COMPAT_MODEL"
log "ANTHROPIC_MODEL=${ANTHROPIC_MODEL:-claude-sonnet-4-6}"
log "MAX_PARALLEL_BASELINES=$MAX_PARALLEL_BASELINES"
log "SUITE_PROGRESS_INTERVAL_SECONDS=$SUITE_PROGRESS_INTERVAL_SECONDS"

log "syncing benchmark assets"
run_logged python3 -u scripts/sync_benchmark_assets.py --benchmark coaction_venue_risk | tee "$LOG_FILE"

log "baseline catalog"
run_logged python3 -u scripts/run_benchmark.py --list-baselines | tee -a "$LOG_FILE"

log "running benchmark suite"
export BENCHMARK_PROGRESS=1

log "effective model routing"
log "openai baselines -> $OPENAI_MODEL" | tee -a "$LOG_FILE"
log "langgraph baseline -> $LANGGRAPH_MODEL" | tee -a "$LOG_FILE"
log "autogen react baseline -> $AUTOGEN_REACT_MODEL" | tee -a "$LOG_FILE"
log "autogen multi-agent baseline -> $AUTOGEN_MULTI_AGENT_MODEL" | tee -a "$LOG_FILE"
log "metagpt baselines -> $METAGPT_MODEL" | tee -a "$LOG_FILE"
log "anthropic baselines -> ${ANTHROPIC_MODEL:-claude-sonnet-4-6}" | tee -a "$LOG_FILE"
log "zeus baseline -> zeus workflow" | tee -a "$LOG_FILE"

run_logged python3 -u scripts/run_all_baselines.py \
  --benchmark coaction_venue_risk \
  --report-root "$REPORT_DIR" \
  --profile current \
  --max-parallel-baselines "$MAX_PARALLEL_BASELINES" \
  --progress-interval-seconds "$SUITE_PROGRESS_INTERVAL_SECONDS" | tee -a "$LOG_FILE"

END_TS="$(date +%s)"
ELAPSED="$((END_TS - START_TS))"

log "done"
log "elapsed_seconds=$ELAPSED"
log "scorecard: $REPORT_DIR/suite_status.md"
