#!/usr/bin/env python3
"""Fetch India job listings per NaukriSala course via SerpApi Google Jobs.

Usage: SERPAPI_KEY=... python3 fetch_serpapi.py
Merges results into jobs.json, deduped by normalized (title, company).
Apply links prefer the employer's direct careers URL (apply_options[0]).
Free plan: 250 searches/month. Usage tracked in serpapi_usage.json.
The key is never printed or stored.
"""
import json, os, re, sys, time, urllib.request, urllib.parse

KEY = os.environ.get("SERPAPI_KEY")
if not KEY:
    sys.exit("Set SERPAPI_KEY env var.")

MONTHLY_LIMIT = 250
SAFETY_CAP = 220

# (slug, label, [queries], pages_per_query, keyword_filter or None)
TRACKS = [
    ("aml-kyc", "AML & KYC Analyst", [
        "KYC analyst", "AML analyst", "anti money laundering analyst",
        "compliance analyst", "financial crime analyst",
        "transaction monitoring analyst", "customer due diligence analyst",
        "risk compliance analyst",
    ], 10, ["aml", "kyc", "know your customer", "anti-money", "anti money",
            "compliance", "financial crime", "transaction monitoring",
            "due diligence", "sanctions", "fraud"]),
    ("servicenow", "ServiceNow Developer", ["ServiceNow developer"], 5, None),
    ("data-science-ai", "Data Science & AI Engineering", ["data scientist machine learning"], 5, None),
    ("stom", "STOM — Service Transition & Ops", ["IT service management"], 5, None),
    ("power-bi", "Power BI Developer", ["Power BI developer"], 5, None),
    ("data-analyst", "Data Analyst", ["data analyst"], 5, None),
    ("workday", "Workday Consultant", ["Workday consultant"], 5, None),
    ("python-fullstack", "Full Stack Python", ["Python full stack developer"], 5, None),
    ("java-fullstack", "Full Stack Java Developer", ["Java full stack developer"], 5, None),
    ("qa-testing", "Software Testing (QA)", ["software testing QA engineer"], 5, None),
    ("ib-operations", "Investment Banking Operations", ["investment banking operations"], 5, None),
    ("sap-fico", "SAP FICO (S/4HANA Finance)", ["SAP FICO consultant"], 5, None),
    ("web-dev", "Web Development", ["web developer"], 5, None),
    ("dotnet", ".NET Developer", [".NET developer"], 5, None),
    ("dbi", "Database & Business Intelligence", ["business intelligence developer"], 5, None),
]

SITE = os.path.dirname(os.path.abspath(__file__))
JOBS_PATH = os.path.join(SITE, "jobs.json")
USAGE_PATH = os.path.join(SITE, "serpapi_usage.json")


def norm(s):
    return re.sub(r"\s+", " ", (s or "").lower().strip())


def usage():
    month = time.strftime("%Y-%m")
    try:
        u = json.load(open(USAGE_PATH))
    except (OSError, ValueError):
        u = {}
    if u.get("month") != month:
        u = {"month": month, "searches": 0}
    return u


def save_usage(u):
    json.dump(u, open(USAGE_PATH, "w"))


def fetch(query, start=0):
    params = {
        "engine": "google_jobs",
        "q": query,
        "location": "India",
        "start": str(start),
        "api_key": KEY,
    }
    url = "https://serpapi.com/search?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as resp:
        return json.load(resp)


def clean(text, n=280):
    t = (text or "").replace("\n", " ").strip()
    return t[:n] + ("…" if len(t) > n else "")


def apply_link(job):
    opts = job.get("apply_options") or []
    if opts:
        return opts[0].get("link")
    return None


def relevant(job, keywords):
    if not keywords:
        return True
    hay = norm(str(job.get("title")) + " " + str(job.get("description")))
    return any(k in hay for k in keywords)


def main():
    u = usage()
    planned = sum(len(q) * p for _, _, q, p, _ in TRACKS)
    if u["searches"] + planned > SAFETY_CAP:
        sys.exit(f"Refusing: {u['searches']} searches used, {planned} more "
                 f"would exceed cap {SAFETY_CAP}/{MONTHLY_LIMIT}.")

    with open(JOBS_PATH) as f:
        data = json.load(f)
    jobs = data["jobs"]
    seen = {(norm(j.get("title")), norm(j.get("company"))) for j in jobs}

    added, spent = 0, 0
    for slug, label, queries, pages, keywords in TRACKS:
        track_added = 0
        for q in queries:
            for p in range(pages):
                try:
                    d = fetch(q, start=p * 10)
                    spent += 1
                except Exception as e:  # noqa: BLE001
                    print(f"[skip] {label} / {q} p{p}: {e}", file=sys.stderr)
                    break
                results = d.get("jobs_results", [])
                if not results:
                    break
                for r in results:
                    link = apply_link(r)
                    if not link or not relevant(r, keywords):
                        continue
                    key = (norm(r.get("title")), norm(r.get("company_name")))
                    if key in seen:
                        continue
                    seen.add(key)
                    ext = r.get("extensions") or []
                    jobs.append({
                        "id": "sp_" + str(r.get("job_id", ""))[:40],
                        "course": slug,
                        "course_label": label,
                        "title": r.get("title"),
                        "company": r.get("company_name"),
                        "location": r.get("location") or "India",
                        "created": None,
                        "contract": "",
                        "snippet": clean(r.get("description")),
                        "url": link,
                        "direct_url": link,
                        "resolved": True,
                        "source": "serpapi",
                        "publisher": r.get("via"),
                        "posted": ", ".join(ext),
                    })
                    track_added += 1
                time.sleep(0.7)
        added += track_added
        print(f"[ok] {label}: {track_added} new jobs")
        time.sleep(0.5)

    u["searches"] += spent
    save_usage(u)
    data["fetched_at"] = time.strftime("%Y-%m-%d")
    data["total"] = len(jobs)
    with open(JOBS_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"Merged {added} SerpApi jobs. Board total: {len(jobs)}. "
          f"SerpApi searches this month: {u['searches']}/{MONTHLY_LIMIT}.")


if __name__ == "__main__":
    main()
