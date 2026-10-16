#!/usr/bin/env python3
"""Weekly expiry sweep for the NaukriSala jobs board.

For each job, fetches its apply URL (direct_url, falling back to url):
- HTTP 404/410            -> expired
- page text matches dead-listing patterns -> expired
- timeout / 403 / 429 / connection error -> unknown, job is KEPT
  (a block is not proof the listing is gone)

Expired jobs are moved to jobs_expired_archive.json (never deleted outright).
Jobs older than STALE_DAYS (by posting date, else pull date) get "stale": true
so the board can badge them as old/unverified listings.

Usage: python3 check_expired.py [--limit N] [--sample]
"""
import json
import os
import re
import sys
import time
import datetime
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

SITE = os.path.dirname(os.path.abspath(__file__))
JP = os.path.join(SITE, "jobs.json")
ARCH = os.path.join(SITE, "jobs_expired_archive.json")
STALE_DAYS = 60
WORKERS = 8
TIMEOUT = 12
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NaukriSala-jobs-board/1.0"}

DEAD_RE = re.compile(
    r"job (has been|is no longer)|(position|vacancy|opening|role) (has been )?filled"
    r"|no longer (available|accepting applications)|applications? (are |is )?closed"
    r"|job not found|listing (has )?expired|this job (posting )?is no longer"
    r"|the position you are looking for (is not|is no longer)",
    re.I)


def check(job):
    url = job.get("direct_url") or job.get("url") or ""
    if not url.startswith("http"):
        return job["id"], "skip"
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            code = r.status
            if code in (404, 410):
                return job["id"], "expired"
            if code != 200:
                return job["id"], "unknown"
            body = r.read(60000).decode("utf-8", "ignore")
            if DEAD_RE.search(body):
                return job["id"], "expired"
            return job["id"], "live"
    except urllib.error.HTTPError as e:
        return job["id"], "expired" if e.code in (404, 410) else "unknown"
    except Exception:
        return job["id"], "unknown"  # timeouts, 403s, DNS: keep the job


def main():
    limit = None
    jobs_all = json.load(open(JP))["jobs"]
    args = sys.argv[1:]
    if "--sample" in args:
        jobs_all = jobs_all[:60]
    if "--limit" in args:
        limit = int(args[args.index("--limit") + 1])
        jobs_all = jobs_all[:limit]

    results = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(check, j): j for j in jobs_all}
        for i, f in enumerate(as_completed(futs), 1):
            jid, status = f.result()
            results[jid] = status
            if i % 200 == 0:
                print(f"  checked {i}/{len(jobs_all)}...", flush=True)

    data = json.load(open(JP))
    jobs = data["jobs"]
    today = datetime.date.today()
    expired, kept = [], []
    for j in jobs:
        st = results.get(j["id"], "unknown")
        # stale flag: older than STALE_DAYS by posting date, else pull date
        ref = j.get("created") or j.get("fetched") or ""
        try:
            age = (today - datetime.date.fromisoformat(ref[:10])).days
        except ValueError:
            age = 0
        j["stale"] = age > STALE_DAYS
        if st == "expired":
            j["expired_on"] = today.isoformat()
            expired.append(j)
        else:
            kept.append(j)

    if expired:
        arch = json.load(open(ARCH)) if os.path.exists(ARCH) else []
        have = {j["id"] for j in arch}
        arch.extend(j for j in expired if j["id"] not in have)
        json.dump(arch, open(ARCH, "w"), ensure_ascii=False)
    data["jobs"] = kept
    data["total"] = len(kept)
    json.dump(data, open(JP, "w"), ensure_ascii=False)
    n_stale = sum(1 for j in kept if j.get("stale"))
    print(f"expired: {len(expired)} (archived), live/unknown kept: {len(kept)}, "
          f"flagged stale (>60d): {n_stale}")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"done in {time.time() - t0:.0f}s")
