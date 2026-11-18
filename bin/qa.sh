#!/usr/bin/env bash
# ==============================================================================
# PrioritySuite Quality Assurance (QA) Script
# Enforces code quality, style, security, and test suite verification.
# ==============================================================================
set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

VENV_BIN="${PROJECT_ROOT}/.venv/bin"

if [ ! -d "${VENV_BIN}" ]; then
    echo "[-] Error: Virtual environment not found at ${PROJECT_ROOT}/.venv"
    exit 1
fi

for candidate in "/usr/local/aws-cli/v2/2.27.11/dist/libsqlite3.so.0" "/usr/local/aws-cli/v2/current/dist/libsqlite3.so.0"; do
    if [ -f "${candidate}" ]; then
        export LD_PRELOAD="${candidate}${LD_PRELOAD:+:${LD_PRELOAD}}"
        break
    fi
done

FAILED_CHECKS=()

run_check() {
    local step_num="$1"
    local name="$2"
    shift 2

    echo "======================================================================"
    echo " [${step_num}/4] Running ${name}..."
    echo "======================================================================"
    if "$@"; then
        echo "[✓] ${name} passed."
    else
        echo "[-] ${name} failed."
        FAILED_CHECKS+=("${name}")
    fi
    echo ""
}

run_check "1" "Ruff (Linting & Style)" "${VENV_BIN}/ruff" check .
run_check "2" "Mypy (Static Type Analysis)" "${VENV_BIN}/mypy" accounts config decisions exports frameworks llm
run_check "3" "Bandit (Security Vulnerability Scan)" "${VENV_BIN}/bandit" -c pyproject.toml -r accounts config decisions exports frameworks llm -q
run_check "4" "Pytest (Full Test Suite)" "${VENV_BIN}/pytest"

echo "======================================================================"
if [ ${#FAILED_CHECKS[@]} -eq 0 ]; then
    echo " [✓] All QA Quality Checks Passed Successfully!"
    echo "======================================================================"
    exit 0
else
    echo " [-] QA FAILED: The following check(s) did not pass:"
    for check in "${FAILED_CHECKS[@]}"; do
        echo "     • ${check}"
    done
    echo "======================================================================"
    exit 1
fi
