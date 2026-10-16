#!/usr/bin/env python3
"""Fetch India job listings per NaukriSala course via the JSearch API (RapidAPI).

Usage: JSEARCH_KEY=... python3 fetch_jsearch.py
Merges results into jobs.json alongside existing listings, deduped by
normalized (title, company). JSearch apply links are direct (employer/publisher
sites) - no redirector, no expiry, no CAPTCHA.

Budget: free tier = 200 requests/month (hard limit). Billing counts PAGES:
one request with num_pages=N consumes N credits (~10 results/page).
TRACKS below declare per-track queries and page depth. Usage tracked in
jsearch_usage.json (credits, not requests) with a safety cap.
The key is never printed or stored.
"""
import json, os, re, sys, time, urllib.request, urllib.parse

KEY = os.environ.get("JSEARCH_KEY")
if not KEY:
    sys.exit("Set JSEARCH_KEY env var.")

MONTHLY_LIMIT = 200
SAFETY_CAP = 180  # stop before hitting the hard limit

# (slug, label, [queries], pages_per_query, keyword_filter or None)
TRACKS = [
    ("aml-kyc", "AML & KYC Analyst", [
        "AML KYC analyst jobs in India",
        "KYC analyst jobs in India",
        "anti money laundering analyst jobs in India",
        "compliance analyst jobs in India",
        "financial crime analyst jobs in India",
        "transaction monitoring analyst jobs in India",
        "customer due diligence analyst jobs in India",
        "risk and compliance analyst jobs in India",
    ], 18, ["aml", "kyc", "know your customer", "anti-money", "anti money",
            "compliance", "financial crime", "transaction monitoring",
            "due diligence", "cdd", "edd", "sanctions", "fraud"]),
    ("servicenow", "ServiceNow Developer", ["ServiceNow developer jobs in India"], 1, None),
    ("data-science-ai", "Data Science & AI Engineering", ["data scientist machine learning jobs in India"], 1, None),
    ("stom", "STOM — Service Transition & Ops", ["IT service management jobs in India"], 1, None),
    ("power-bi", "Power BI Developer", ["Power BI developer jobs in India"], 1, None),
    ("data-analyst", "Data Analyst", ["data analyst jobs in India"], 1, None),
    ("workday", "Workday Consultant", ["Workday consultant jobs in India"], 1, None),
    ("python-fullstack", "Full Stack Python", ["Python full stack developer jobs in India"], 1, None),
    ("java-fullstack", "Full Stack Java Developer", ["Java full stack developer jobs in India"], 1, None),
    ("qa-testing", "Software Testing (QA)", ["software testing QA engineer jobs in India"], 1, None),
    ("ib-operations", "Investment Banking Operations", ["investment banking operations jobs in India"], 1, None),
    ("sap-fico", "SAP FICO (S/4HANA Finance)", ["SAP FICO consultant jobs in India"], 1, None),
    ("web-dev", "Web Development", ["web developer jobs in India"], 1, None),
    ("dotnet", ".NET Developer", [".NET developer jobs in India"], 1, None),
    ("dbi", "Database & Business Intelligence", ["business intelligence developer jobs in India"], 1, None),
]

SITE = os.path.dirname(os.path.abspath(__file__))
JOBS_PATH = os.path.join(SITE, "jobs.json")
USAGE_PATH = os.path.join(SITE, "jsearch_usage.json")


def norm(s):
    return re.sub(r"\s+", " ", (s or "").lower().strip())


def usage():
    month = time.strftime("%Y-%m")
    try:
        u = json.load(open(USAGE_PATH))
    except (OSError, ValueError):
        u = {}
    if u.get("month") != month:
        u = {"month": month, "credits": 0}
    # migrate old request-based counter conservatively (1 req ~= 1 credit)
    if "calls" in u and "credits" not in u:
        u["credits"] = u.pop("calls")
    return u


def save_usage(u):
    json.dump(u, open(USAGE_PATH, "w"))


def fetch(query, num_pages=1):
    params = {
        "query": query,
        "num_pages": str(num_pages),
        "country": "in",
        "date_posted": "month",
    }
    url = "https://jsearch.p.rapidapi.com/search-v2?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "X-RapidAPI-Key": KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    })
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.load(resp)


def clean(text, n=280):
    t = (text or "").replace("\n", " ").strip()
    return t[:n] + ("…" if len(t) > n else "")


def relevant(job, keywords):
    if not keywords:
        return True
    hay = norm(str(job.get("job_title")) + " " + str(job.get("job_description")))
    return any(k in hay for k in keywords)


def main():
    u = usage()
    planned = sum(len(q) * p for _, _, q, p, _ in TRACKS)
    if u["credits"] + planned > SAFETY_CAP:
        sys.exit(f"Refusing: {u['credits']} credits used this month, "
                 f"{planned} more would exceed safety cap {SAFETY_CAP}/{MONTHLY_LIMIT}.")

    with open(JOBS_PATH) as f:
        data = json.load(f)
    jobs = data["jobs"]
    seen = {(norm(j.get("title")), norm(j.get("company"))) for j in jobs}

    added, spent = 0, 0
    for slug, label, queries, pages, keywords in TRACKS:
        track_added = 0
        for query in queries:
            try:
                d = fetch(query, pages)
                spent += pages
            except Exception as e:  # noqa: BLE001 - keep going on per-query errors
                print(f"[skip] {label} / {query[:40]}: {e}", file=sys.stderr)
                continue
            if d.get("status") != "OK":
                print(f"[skip] {label}: API status {d.get('status')}", file=sys.stderr)
                continue
            payload = d.get("data", [])
            results = payload if isinstance(payload, list) else payload.get("jobs", [])
            for r in results:
                if not r.get("job_apply_link") or not relevant(r, keywords):
                    continue
                key = (norm(r.get("job_title")), norm(r.get("employer_name")))
                if key in seen:
                    continue
                seen.add(key)
                jobs.append({
                    "id": "js_" + str(r.get("job_id", ""))[:40],
                    "course": slug,
                    "course_label": label,
                    "title": r.get("job_title"),
                    "company": r.get("employer_name"),
                    "location": r.get("job_location") or r.get("job_city") or "India",
                    "created": r.get("job_posted_at_datetime_utc"),
                    "contract": (r.get("job_employment_type") or "").lower(),
                    "snippet": clean(r.get("job_description")),
                    "url": r.get("job_apply_link"),
                    "direct_url": r.get("job_apply_link"),
                    "resolved": True,
                    "source": "jsearch",
                    "publisher": r.get("job_publisher"),
                    "salary_min": r.get("job_min_salary"),
                    "salary_max": r.get("job_max_salary"),
                    "salary_currency": r.get("job_salary_currency"),
                    "salary_period": r.get("job_salary_period"),
                    "employer_website": r.get("employer_website"),
                })
                track_added += 1
            time.sleep(1)
        added += track_added
        print(f"[ok] {label}: {track_added} new jobs ({len(queries)}x{pages}p)")
        time.sleep(1)

    u["credits"] += spent
    save_usage(u)
    data["fetched_at"] = time.strftime("%Y-%m-%d")
    data["total"] = len(jobs)
    with open(JOBS_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"Merged {added} JSearch jobs. Board total: {len(jobs)}. "
          f"JSearch credits this month: {u['credits']}/{MONTHLY_LIMIT}.")


if __name__ == "__main__":
    main()
