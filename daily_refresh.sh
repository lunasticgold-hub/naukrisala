#!/bin/bash
# NaukriSala jobs board — daily backend refresh.
# Runs all fetchers (quota-limited ones self-skip when credits are exhausted),
# bumps the jobs.json cache-buster, commits and pushes to GitHub Pages.
# Called by the daily cron; safe to run manually too.
set -u
cd "$(dirname "$0")"

# API keys for the daily run (Jooble; Adzuna held, see below): stored in a
# locked file OUTSIDE this repo (0600, this account only) — never committed.
if [ -f "$HOME/.config/naukrisala/secrets.env" ]; then
  set -a; . "$HOME/.config/naukrisala/secrets.env"; set +a
fi

echo "=== refresh start: $(date -u +%FT%TZ) ==="

python3 fetch_ats.py 2>&1 | tail -3 || echo "[warn] fetch_ats failed"
python3 fetch_ats2.py 2>&1 | tail -3 || echo "[warn] fetch_ats2 failed"
python3 fetch_enterprise.py 2>&1 | tail -5 || echo "[warn] fetch_enterprise failed"
# AML-focused boards (verified 2026-10-24): strict aml_gate relevance only
python3 fetch_aml_boards.py 2>&1 | tail -3 || echo "[warn] fetch_aml_boards failed"
# Browser-boards engine (custom/SPA career pages; no-op until boards added)
python3 fetch_browser_boards.py 2>&1 | tail -3 || echo "[warn] fetch_browser_boards failed"
python3 fetch_jsearch.py 2>&1 | tail -2 || echo "[info] jsearch skipped (quota or error)"
python3 fetch_serpapi.py 2>&1 | tail -2 || echo "[info] serpapi skipped (quota or error)"

# Adzuna: HELD — key is test-tier only (25 calls, pending activation); the
# daily run must NOT consume it until the paid/free decision is made.
# python3 fetch_adzuna_aml.py 2>&1 | tail -2 || echo "[info] adzuna held (test tier)"
# Jooble: ~76 calls/run with 0.5s delays; skips cleanly without JOOBLE_KEY
python3 fetch_jooble.py 2>&1 | tail -2 || echo "[info] jooble skipped (no key or error)"
# WhatJobs: keyless publisher feed
python3 fetch_whatjobs.py 2>&1 | tail -2 || echo "[info] whatjobs skipped (error)"

# normalize new jobs (pull-date stamp, contract/city cleanup) and sort newest-first
python3 normalize_jobs.py 2>&1 | tail -2 || echo "[warn] normalize failed"

# bump cache-buster so browsers pick up the fresh jobs.json
V=$(date +%Y%m%d)
sed -i "s|jobs.json?v=[0-9]*[a-z]*|jobs.json?v=${V}|" jobs.html

if git diff --quiet jobs.json jobs.html; then
  echo "no changes to push"
  exit 0
fi

git add jobs.json jobs.html ats_boards.json ats_boards2.json enterprise_boards.json aml_boards.json browser_boards.json \
        jsearch_usage.json serpapi_usage.json 2>/dev/null
N=$(python3 -c "import json; print(json.load(open('jobs.json'))['total'])")
AML=$(python3 -c "
import json
d = json.load(open('jobs.json'))
print(sum(1 for j in d['jobs'] if j.get('course')=='aml-kyc'))")
git commit -q -m "Jobs: daily refresh (board: ${N}, ${AML} AML/KYC)"
git push -q
echo "pushed OK — board total: ${N}, AML/KYC: ${AML}"
