#!/bin/bash
# NaukriSala jobs board — daily backend refresh.
# Runs all fetchers (quota-limited ones self-skip when credits are exhausted),
# bumps the jobs.json cache-buster, commits and pushes to GitHub Pages.
# Called by the daily cron; safe to run manually too.
set -u
cd "$(dirname "$0")"

echo "=== refresh start: $(date -u +%FT%TZ) ==="

python3 fetch_ats.py 2>&1 | tail -3 || echo "[warn] fetch_ats failed"
python3 fetch_enterprise.py 2>&1 | tail -5 || echo "[warn] fetch_enterprise failed"
python3 fetch_jsearch.py 2>&1 | tail -2 || echo "[info] jsearch skipped (quota or error)"
python3 fetch_serpapi.py 2>&1 | tail -2 || echo "[info] serpapi skipped (quota or error)"

# normalize new jobs (pull-date stamp, contract/city cleanup) and sort newest-first
python3 normalize_jobs.py 2>&1 | tail -2 || echo "[warn] normalize failed"

# bump cache-buster so browsers pick up the fresh jobs.json
V=$(date +%Y%m%d)
sed -i "s|jobs.json?v=[0-9]*[a-z]*|jobs.json?v=${V}|" jobs.html

if git diff --quiet jobs.json jobs.html; then
  echo "no changes to push"
  exit 0
fi

git add jobs.json jobs.html ats_boards.json enterprise_boards.json \
        jsearch_usage.json serpapi_usage.json 2>/dev/null
N=$(python3 -c "import json; print(json.load(open('jobs.json'))['total'])")
AML=$(python3 -c "
import json
d = json.load(open('jobs.json'))
print(sum(1 for j in d['jobs'] if j.get('course')=='aml-kyc'))")
git commit -q -m "Jobs: daily refresh (board: ${N}, ${AML} AML/KYC)"
git push -q
echo "pushed OK — board total: ${N}, AML/KYC: ${AML}"
