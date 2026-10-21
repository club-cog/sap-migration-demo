#!/usr/bin/env bash
# Regenerate legacy/reference_outputs/*.csv from the Quill models (RiskDB emulation).
# Usage: legacy/run_all.sh [--check] [--model NAME]
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 -m legacy.quill_runtime.run_all "$@"
