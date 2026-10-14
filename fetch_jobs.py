#!/usr/bin/env python3
"""Fetch India job listings per NaukriSala course via the Adzuna Jobs API.

Usage: ADZUNA_APP_ID=... ADZUNA_KEY=... python3 fetch_jobs.py
Writes jobs.json next to this script. One API call per course.
The key is never printed or stored.
"""
import json, os, sys, time, urllib.request, urllib.parse

APP_ID = os.environ.get("ADZUNA_APP_ID")
APP_KEY = os.environ.get("ADZUNA_KEY")
if not APP_ID or not APP_KEY:
    sys.exit("Set ADZUNA_APP_ID and ADZUNA_KEY env vars.")

COURSES = [
    ("aml-kyc", "AML & KYC Analyst", "AML KYC analyst"),
    ("servicenow", "ServiceNow Developer", "ServiceNow developer"),
    ("data-science-ai", "Data Science & AI Engineering", "data scientist machine learning"),
    ("stom", "STOM — Service Transition & Ops", "IT service management"),
    ("power-bi", "Power BI Developer", "Power BI developer"),
    ("data-analyst", "Data Analyst", "data analyst"),
    ("workday", "Workday Consultant", "Workday consultant"),
    ("python-fullstack", "Full Stack Python", "Python full stack developer"),
    ("java-fullstack", "Full Stack Java Developer", "Java full stack developer"),
    ("qa-testing", "Software Testing (QA)", "software testing QA engineer"),
    ("ib-operations", "Investment Banking Operations", "investment banking operations"),
    ("sap-fico", "SAP FICO (S/4HANA Finance)", "SAP FICO consultant"),
    ("web-dev", "Web Development", "web developer"),
    ("dotnet", ".NET Developer", ".NET developer"),
    ("dbi", "Database & Business Intelligence", "business intelligence developer"),
]

def fetch(what):
    params = {
        "app_id": APP_ID, "app_key": APP_KEY,
        "what": what, "results_per_page": 40,
        "sort_by": "date", "max_days_old": 60,
    }
    url = "https://api.adzuna.com/v1/api/jobs/in/search/1?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)

def clean(text, n=280):
    t = (text or "").replace("\n", " ").strip()
    return t[:n] + ("…" if len(t) > n else "")

jobs, seen = [], set()
for slug, label, query in COURSES:
    try:
        data = fetch(query)
    except Exception as e:  # noqa: BLE001 - keep going on per-course errors
        print(f"[skip] {label}: {e}", file=sys.stderr)
        continue
    n = 0
    for r in data.get("results", []):
        jid = str(r.get("id"))
        if jid in seen:
            continue
        seen.add(jid)
        jobs.append({
            "id": jid,
            "course": slug,
            "course_label": label,
            "title": r.get("title"),
            "company": (r.get("company") or {}).get("display_name"),
            "location": (r.get("location") or {}).get("display_name"),
            "created": r.get("created"),
            "contract": r.get("contract_time"),
            "category": (r.get("category") or {}).get("label"),
            "snippet": clean(r.get("description")),
            "url": r.get("redirect_url"),
        })
        n += 1
    print(f"[ok] {label}: {n} jobs (total matches: {data.get('count')})")
    time.sleep(1)

payload = {
    "fetched_at": time.strftime("%Y-%m-%d"),
    "source": "Adzuna Jobs API (India)",
    "total": len(jobs),
    "jobs": jobs,
}
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jobs.json")
with open(out, "w") as f:
    json.dump(payload, f, ensure_ascii=False)
print(f"Wrote {out}: {len(jobs)} jobs.")
