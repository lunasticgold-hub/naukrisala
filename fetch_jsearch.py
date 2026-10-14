#!/usr/bin/env python3
"""Fetch India job listings per NaukriSala course via the JSearch API (RapidAPI).

Usage: JSEARCH_KEY=... python3 fetch_jsearch.py
Merges results into jobs.json alongside existing Adzuna listings, deduped by
normalized (title, company). JSearch apply links are direct (employer/publisher
sites) - no redirector, no expiry, no CAPTCHA.

Budget: free tier = 200 requests/month (hard limit). One request = one page
(~10 results). This script uses 15 calls per full refresh (1 page x 15 tracks).
A usage counter in jsearch_usage.json refuses to run past a safety cap.
The key is never printed or stored.
"""
import json, os, re, sys, time, urllib.request, urllib.parse

KEY = os.environ.get("JSEARCH_KEY")
if not KEY:
    sys.exit("Set JSEARCH_KEY env var.")

MONTHLY_LIMIT = 200
SAFETY_CAP = 180  # stop refreshing before hitting the hard limit

COURSES = [
    ("aml-kyc", "AML & KYC Analyst", "AML KYC analyst jobs in India"),
    ("servicenow", "ServiceNow Developer", "ServiceNow developer jobs in India"),
    ("data-science-ai", "Data Science & AI Engineering", "data scientist machine learning jobs in India"),
    ("stom", "STOM — Service Transition & Ops", "IT service management jobs in India"),
    ("power-bi", "Power BI Developer", "Power BI developer jobs in India"),
    ("data-analyst", "Data Analyst", "data analyst jobs in India"),
    ("workday", "Workday Consultant", "Workday consultant jobs in India"),
    ("python-fullstack", "Full Stack Python", "Python full stack developer jobs in India"),
    ("java-fullstack", "Full Stack Java Developer", "Java full stack developer jobs in India"),
    ("qa-testing", "Software Testing (QA)", "software testing QA engineer jobs in India"),
    ("ib-operations", "Investment Banking Operations", "investment banking operations jobs in India"),
    ("sap-fico", "SAP FICO (S/4HANA Finance)", "SAP FICO consultant jobs in India"),
    ("web-dev", "Web Development", "web developer jobs in India"),
    ("dotnet", ".NET Developer", ".NET developer jobs in India"),
    ("dbi", "Database & Business Intelligence", "business intelligence developer jobs in India"),
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
        u = {"month": month, "calls": 0}
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
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def clean(text, n=280):
    t = (text or "").replace("\n", " ").strip()
    return t[:n] + ("…" if len(t) > n else "")


def main():
    u = usage()
    planned = len(COURSES)  # 1 page per track
    if u["calls"] + planned > SAFETY_CAP:
        sys.exit(f"Refusing: {u['calls']} calls used this month, "
                 f"{planned} more would exceed safety cap {SAFETY_CAP}/{MONTHLY_LIMIT}.")

    with open(JOBS_PATH) as f:
        data = json.load(f)
    jobs = data["jobs"]
    seen = {(norm(j.get("title")), norm(j.get("company"))) for j in jobs}

    added, calls = 0, 0
    for slug, label, query in COURSES:
        try:
            d = fetch(query)
            calls += 1
        except Exception as e:  # noqa: BLE001 - keep going on per-course errors
            print(f"[skip] {label}: {e}", file=sys.stderr)
            continue
        if d.get("status") != "OK":
            print(f"[skip] {label}: API status {d.get('status')}", file=sys.stderr)
            continue
        payload = d.get("data", [])
        results = payload if isinstance(payload, list) else payload.get("jobs", [])
        n = 0
        for r in results:
            key = (norm(r.get("job_title")), norm(r.get("employer_name")))
            if key in seen or not r.get("job_apply_link"):
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
            })
            n += 1
        added += n
        print(f"[ok] {label}: {n} new jobs")
        time.sleep(1)

    u["calls"] += calls
    save_usage(u)
    data["fetched_at"] = time.strftime("%Y-%m-%d")
    data["total"] = len(jobs)
    with open(JOBS_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"Merged {added} JSearch jobs. Board total: {len(jobs)}. "
          f"JSearch calls this month: {u['calls']}/{MONTHLY_LIMIT}.")


if __name__ == "__main__":
    main()
