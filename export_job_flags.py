#!/usr/bin/env python3
"""Export admin-hidden job ids (ns_job_flags) to job_flags.json for the daily refresh.

Reads SUPABASE_NS_URL + SUPABASE_NS_SERVICE_KEY from the environment (sourced
from ~/.config/naukrisala/secrets.env by daily_refresh.sh). Best-effort only:
any failure prints a warning and leaves job_flags.json untouched, so the
refresh never aborts because of this step. With no flags it writes an empty
list, which normalize treats as a no-op.
"""
import json
import os
import sys
import urllib.request
import urllib.error

SITE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(SITE, "job_flags.json")


def main():
    url = os.environ.get("SUPABASE_NS_URL")
    key = os.environ.get("SUPABASE_NS_SERVICE_KEY")
    if not url or not key:
        print("[warn] export_job_flags: SUPABASE_NS_* not set, skipping (no flags applied)")
        return 0
    try:
        req = urllib.request.Request(
            f"{url}/rest/v1/ns_job_flags?select=job_id,action&action=eq.hide")
        req.add_header("apikey", key)
        req.add_header("Authorization", f"Bearer {key}")
        with urllib.request.urlopen(req, timeout=30) as resp:
            rows = json.load(resp)
    except Exception as e:
        print(f"[warn] export_job_flags: fetch failed ({e}), skipping (no flags applied)")
        return 0
    ids = sorted({r["job_id"] for r in rows if r.get("job_id")})
    tmp = OUT + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"job_ids": ids}, f)
    os.replace(tmp, OUT)
    print(f"export_job_flags: {len(ids)} hidden job ids -> job_flags.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
