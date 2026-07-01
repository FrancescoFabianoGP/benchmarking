#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="${1:-reports/runs/coaction_all_baselines_gpt55}"
LOG_DIR="$REPORT_DIR"
LOG_FILE="$LOG_DIR/run.log"

cd "$ROOT_DIR"

mkdir -p "$LOG_DIR"

echo "[coaction-suite] repo: $ROOT_DIR"
echo "[coaction-suite] report dir: $REPORT_DIR"
echo "[coaction-suite] log file: $LOG_FILE"

if [[ -f .env ]]; then
  echo "[coaction-suite] loading .env"
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
else
  echo "[coaction-suite] no .env found, using current shell environment"
fi

export OPENAI_MODEL="${OPENAI_MODEL:-gpt-5.5}"
export BENCHMARK_FRAMEWORK_MODEL="${BENCHMARK_FRAMEWORK_MODEL:-gpt-5.5}"
export AUTOGEN_REACT_MODEL="${AUTOGEN_REACT_MODEL:-gpt-5.5}"
export AUTOGEN_MULTI_AGENT_MODEL="${AUTOGEN_MULTI_AGENT_MODEL:-gpt-5.5}"
export LANGGRAPH_MODEL="${LANGGRAPH_MODEL:-gpt-5.5}"
export METAGPT_MODEL="${METAGPT_MODEL:-gpt-5.5}"
export PYTHONUNBUFFERED=1

echo "[coaction-suite] OPENAI_MODEL=$OPENAI_MODEL"
echo "[coaction-suite] BENCHMARK_FRAMEWORK_MODEL=$BENCHMARK_FRAMEWORK_MODEL"

echo "[coaction-suite] syncing benchmark assets"
python3 -u scripts/sync_benchmark_assets.py --benchmark coaction_venue_risk | tee "$LOG_FILE"

echo "[coaction-suite] baseline catalog"
python3 -u scripts/run_benchmark.py --list-baselines | tee -a "$LOG_FILE"

echo "[coaction-suite] running benchmark suite"
export BENCHMARK_PROGRESS=1

echo "[coaction-suite] effective model routing"
echo "[coaction-suite] openai baselines -> $OPENAI_MODEL" | tee -a "$LOG_FILE"
echo "[coaction-suite] langgraph baseline -> $LANGGRAPH_MODEL" | tee -a "$LOG_FILE"
echo "[coaction-suite] autogen react baseline -> $AUTOGEN_REACT_MODEL" | tee -a "$LOG_FILE"
echo "[coaction-suite] autogen multi-agent baseline -> $AUTOGEN_MULTI_AGENT_MODEL" | tee -a "$LOG_FILE"
echo "[coaction-suite] metagpt baselines -> $METAGPT_MODEL" | tee -a "$LOG_FILE"
echo "[coaction-suite] anthropic baselines -> ${ANTHROPIC_MODEL:-claude-sonnet-4-6}" | tee -a "$LOG_FILE"
echo "[coaction-suite] zeus baseline -> zeus workflow" | tee -a "$LOG_FILE"

python3 -u scripts/run_all_baselines.py \
  --benchmark coaction_venue_risk \
  --report-root "$REPORT_DIR" \
  --profile current | tee -a "$LOG_FILE"

echo "[coaction-suite] done"
echo "[coaction-suite] scorecard: $REPORT_DIR/suite_status.md"
