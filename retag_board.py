#!/usr/bin/env python3
"""Re-tag every job on the board with the strict classifier.

Why: older jobs were tagged by loose per-fetcher rules (broad keywords,
description boilerplate), so ~1 in 3 tags came from the description only
and plainly wrong tags appeared (e.g. "Senior Software Engineer" tagged
AML & KYC). This pass re-derives each job's course from its stored
title + snippet using fetch_browser_boards.classify() — first matching
course wins, aml-kyc additionally requires aml_gate() — and moves jobs
matching NO course into a "general" course instead of deleting them
(user decision 2026-10-24).

Exempt from re-tagging: sources "aml-boards" and "browser-boards".
Those were already gated on their FULL descriptions at fetch time;
re-tagging them on the 280-char snippet could only degrade them.

Usage: python3 retag_board.py [--dry-run]
Idempotent; safe to run in the daily refresh after normalize.
"""
import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_ats import TRACK_LABELS
from fetch_browser_boards import classify

SITE = os.path.dirname(os.path.abspath(__file__))
JOBS_PATH = os.path.join(SITE, "jobs.json")
EXEMPT_SOURCES = {"aml-boards", "browser-boards"}
GENERAL_LABEL = "General"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data = json.load(open(JOBS_PATH))
    jobs = data["jobs"]
    before, after = Counter(), Counter()
    changed, to_general, exempt = 0, 0, []
    samples = []
    for j in jobs:
        old = j.get("course")
        before[old] += 1
        if j.get("source") in EXEMPT_SOURCES:
            after[old] += 1
            exempt.append(j)
            continue
        new = classify(j.get("title"), j.get("snippet") or "") or "general"
        if new != old:
            changed += 1
            if new == "general":
                to_general += 1
            if len(samples) < 15:
                samples.append((j.get("title"), j.get("company"), old, new))
        j["course"] = new
        j["course_label"] = (TRACK_LABELS[new] if new in TRACK_LABELS
                             else GENERAL_LABEL)
        after[new] += 1

    print(f"jobs: {len(jobs)} | tags changed: {changed} "
          f"| moved to General: {to_general} "
          f"| exempt (already strict-gated): {len(exempt)}")
    print("before:", dict(before))
    print("after: ", dict(after))
    print("sample changes (title | company | old -> new):")
    for t, c, o, n in samples:
        print(f"  - {t} | {c} | {o} -> {n}")
    if args.dry_run:
        print("DRY RUN — jobs.json untouched.")
        return
    data["total"] = len(jobs)
    with open(JOBS_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    print("jobs.json rewritten.")


if __name__ == "__main__":
    main()
