#!/usr/bin/env bash
# Security scanning — Phase 13
# Run from the project root: bash scripts/run_security_scan.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="$ROOT/security_scan_reports"
mkdir -p "$REPORT_DIR"

echo "================================================================"
echo " Network Attack Simulator — Security Scan"
echo " $(date)"
echo "================================================================"

# ── 1. Semgrep (static analysis — Python backend) ────────────────────
echo ""
echo "[ 1/2 ] Semgrep — static analysis (backend/)"

if ! command -v semgrep &>/dev/null; then
    # pip-installed semgrep may not be on PATH; check common locations
    SEMGREP_BIN=""
    for candidate in \
        "$(python3 -m site --user-base 2>/dev/null)/bin/semgrep" \
        "/Library/Frameworks/Python.framework/Versions/3.11/bin/semgrep" \
        "$HOME/.local/bin/semgrep"; do
        if [[ -x "$candidate" ]]; then
            SEMGREP_BIN="$candidate"
            break
        fi
    done

    if [[ -z "$SEMGREP_BIN" ]]; then
        echo "  ERROR: semgrep not found. Install with: pip install semgrep"
        echo "  Skipping semgrep scan."
        SEMGREP_OK=false
    else
        echo "  Found semgrep at $SEMGREP_BIN"
        SEMGREP_OK=true
    fi
else
    SEMGREP_BIN="semgrep"
    SEMGREP_OK=true
fi

if [[ "$SEMGREP_OK" == "true" ]]; then
    SEMGREP_JSON="$REPORT_DIR/semgrep_report.json"
    echo "  Running semgrep --config=auto backend/ ..."
    "$SEMGREP_BIN" \
        --config=auto \
        "$ROOT/backend/" \
        --json \
        --output "$SEMGREP_JSON" \
        --quiet \
        || true   # semgrep exits non-zero when findings exist; don't abort

    FINDING_COUNT=$(python3 -c "
import json, sys
try:
    d = json.load(open('$SEMGREP_JSON'))
    print(len(d.get('results', [])))
except Exception:
    print('?')
")
    echo "  Done. Findings: $FINDING_COUNT"
    echo "  Report: $SEMGREP_JSON"
fi

# ── 2. Snyk (dependency vuln scanning) ────────────────────────────────
echo ""
echo "[ 2/2 ] Snyk — dependency vulnerability scan"

if [[ -z "${SNYK_TOKEN:-}" ]]; then
    echo "  SNYK_TOKEN is not set — skipping Snyk scan."
    echo "  To enable: set SNYK_TOKEN=<your-free-token> and re-run."
    echo "  Free account: https://app.snyk.io/login"
    echo ""
    echo "  As an alternative, you can run these manually (no account needed):"
    echo "    pip-audit -r backend/requirements.txt"
    echo "    npm audit --json > security_scan_reports/npm_audit.json  (cd frontend/)"
else
    if ! command -v snyk &>/dev/null; then
        echo "  ERROR: snyk CLI not found. Install with: npm install -g snyk"
        echo "  Skipping Snyk scan."
    else
        echo "  Scanning backend/requirements.txt ..."
        snyk test \
            --file="$ROOT/backend/requirements.txt" \
            --package-manager=pip \
            --json \
            > "$REPORT_DIR/snyk_backend.json" 2>&1 \
            || true

        echo "  Scanning frontend/package.json ..."
        snyk test \
            --file="$ROOT/frontend/package.json" \
            --json \
            > "$REPORT_DIR/snyk_frontend.json" 2>&1 \
            || true

        echo "  Done. Reports: $REPORT_DIR/snyk_backend.json, $REPORT_DIR/snyk_frontend.json"
    fi
fi

echo ""
echo "================================================================"
echo " Scan complete. Reports in: $REPORT_DIR/"
echo " See SECURITY_SCAN.md for findings summary and triage decisions."
echo "================================================================"
