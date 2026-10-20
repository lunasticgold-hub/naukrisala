#!/usr/bin/env python3
"""Deep AML/KYC pull from Adzuna (remaining test-plan calls).

Usage: ADZUNA_APP_ID=... ADZUNA_KEY=... python3 fetch_adzuna_aml.py
Runs up to 8 queries (the remaining test calls), 50 results each, merged into
jobs.json with dedup. Credentials are never printed or stored.
"""
import json, os, re, sys, time, urllib.request, urllib.parse

APP_ID = os.environ.get("ADZUNA_APP_ID")
APP_KEY = os.environ.get("ADZUNA_KEY")
if not APP_ID or not APP_KEY:
    sys.exit("Set ADZUNA_APP_ID and ADZUNA_KEY env vars.")

QUERIES = [
    "AML KYC analyst",
    "KYC analyst",
    "compliance analyst",
    "financial crime analyst",
    "transaction monitoring analyst",
    "due diligence analyst",
    "anti money laundering",
    "risk compliance analyst",
]
MAX_CALLS = 8

SITE = os.path.dirname(os.path.abspath(__file__))
JOBS_PATH = os.path.join(SITE, "jobs.json")

KEYWORDS = ["aml", "kyc", "know your customer", "anti-money", "anti money",
            "compliance", "financial crime", "transaction monitoring",
            "due diligence", "sanctions", "fraud"]


def norm(s):
    return re.sub(r"\s+", " ", (s or "").lower().strip())


def fetch(what):
    params = {
        "app_id": APP_ID, "app_key": APP_KEY,
        "what": what, "results_per_page": 50,
        "sort_by": "date", "max_days_old": 60,
    }
    url = "https://api.adzuna.com/v1/api/jobs/in/search/1?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)


def clean(text, n=280):
    t = (text or "").replace("\n", " ").strip()
    return t[:n] + ("…" if len(t) > n else "")


def main():
    with open(JOBS_PATH) as f:
        data = json.load(f)
    jobs = data["jobs"]
    seen = {(norm(j.get("title")), norm(j.get("company"))) for j in jobs}

    added = 0
    for i, q in enumerate(QUERIES[:MAX_CALLS]):
        try:
            d = fetch(q)
        except Exception as e:  # noqa: BLE001
            print(f"[skip] {q}: {e}", file=sys.stderr)
            continue
        n = 0
        for r in d.get("results", []):
            hay = norm(str(r.get("title")) + " " + str(r.get("description")))
            if not any(k in hay for k in KEYWORDS):
                continue
            key = (norm(r.get("title")), norm((r.get("company") or {}).get("display_name")))
            if key in seen:
                continue
            seen.add(key)
            jobs.append({
                "id": str(r.get("id")),
                "source": "adzuna",
                "course": "aml-kyc",
                "course_label": "AML & KYC Analyst",
                "title": r.get("title"),
                "company": (r.get("company") or {}).get("display_name"),
                "location": (r.get("location") or {}).get("display_name"),
                "created": r.get("created"),
                "contract": r.get("contract_time"),
                "category": (r.get("category") or {}).get("label"),
                "snippet": clean(r.get("description")),
                "url": r.get("redirect_url"),
                "salary_min": r.get("salary_min"),
                "salary_max": r.get("salary_max"),
                "salary_currency": "INR",
            })
            n += 1
        added += n
        print(f"[ok] {q}: {n} new (total matches: {d.get('count')})")
        time.sleep(1)

    data["fetched_at"] = time.strftime("%Y-%m-%d")
    data["total"] = len(jobs)
    with open(JOBS_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"Merged {added} Adzuna AML/KYC jobs. Board total: {len(jobs)}.")


if __name__ == "__main__":
    main()
