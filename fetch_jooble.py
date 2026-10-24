#!/usr/bin/env python3
"""Fetch India job listings per NaukriSala course via the Jooble API.

Usage: JOOBLE_KEY=... python3 fetch_jooble.py
Merges results into jobs.json, deduped by normalized (title, company).
Jooble apply links (jooble.org/jdp/...) are stable, non-expiring, and have no
CAPTCHA — one click from the employer apply page.
The key is never printed or stored.
"""
import json, os, re, sys, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_ats import aml_gate  # shared v2 title-led AML/KYC relevance gate

KEY = os.environ.get("JOOBLE_KEY")
if not KEY:
    sys.exit("Set JOOBLE_KEY env var.")

# (slug, label, [keywords], max_pages, keyword_filter or None)
TRACKS = [
    ("aml-kyc", "AML & KYC Analyst", [
        "KYC analyst", "AML analyst", "anti money laundering",
        "compliance analyst", "financial crime", "transaction monitoring",
        "customer due diligence", "risk compliance",
    ], 6, ["aml", "kyc", "know your customer", "anti-money", "anti money",
           "compliance", "financial crime", "transaction monitoring",
           "due diligence", "sanctions", "fraud"]),
    ("servicenow", "ServiceNow Developer", ["ServiceNow developer"], 2, None),
    ("data-science-ai", "Data Science & AI Engineering", ["data scientist machine learning"], 2, None),
    ("stom", "STOM — Service Transition & Ops", ["IT service management"], 2, None),
    ("power-bi", "Power BI Developer", ["Power BI developer"], 2, None),
    ("data-analyst", "Data Analyst", ["data analyst"], 2, None),
    ("workday", "Workday Consultant", ["Workday consultant"], 2, None),
    ("python-fullstack", "Full Stack Python", ["Python full stack developer"], 2, None),
    ("java-fullstack", "Full Stack Java Developer", ["Java full stack developer"], 2, None),
    ("qa-testing", "Software Testing (QA)", ["software testing QA"], 2, None),
    ("ib-operations", "Investment Banking Operations", ["investment banking operations"], 2, None),
    ("sap-fico", "SAP FICO (S/4HANA Finance)", ["SAP FICO consultant"], 2, None),
    ("web-dev", "Web Development", ["web developer"], 2, None),
    ("dotnet", ".NET Developer", [".NET developer"], 2, None),
    ("dbi", "Database & Business Intelligence", ["business intelligence developer"], 2, None),
]

SITE = os.path.dirname(os.path.abspath(__file__))
JOBS_PATH = os.path.join(SITE, "jobs.json")


def norm(s):
    return re.sub(r"\s+", " ", (s or "").lower().strip())


def clean(text, n=280):
    t = re.sub(r"<[^>]+>", " ", text or "")
    t = re.sub(r"\s+", " ", t).replace("&nbsp;", " ").strip()
    return t[:n] + ("…" if len(t) > n else "")


def fetch(keywords, location="India", page=1):
    body = json.dumps({"keywords": keywords, "location": location, "page": page}).encode()
    req = urllib.request.Request(
        "https://in.jooble.org/api/" + KEY, data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def relevant(job, keywords):
    if not keywords:
        return True
    hay = norm(str(job.get("title")) + " " + str(job.get("snippet")))
    return any(k in hay for k in keywords)


def main():
    with open(JOBS_PATH) as f:
        data = json.load(f)
    jobs = data["jobs"]
    seen = {(norm(j.get("title")), norm(j.get("company"))) for j in jobs}

    added = 0
    only = os.environ.get("JOOBLE_TRACKS")
    tracks = [t for t in TRACKS if t[0] in only.split(",")] if only else TRACKS
    for slug, label, queries, max_pages, keywords in tracks:
        track_added = 0
        for q in queries:
            for page in range(1, max_pages + 1):
                try:
                    d = fetch(q, page=page)
                except Exception as e:  # noqa: BLE001
                    print(f"[skip] {label} / {q} p{page}: {e}", file=sys.stderr)
                    break
                results = d.get("jobs", [])
                if not results:
                    break
                for r in results:
                    if not r.get("link"):
                        continue
                    # AML/KYC track: shared v2 title-led gate (boilerplate-proof).
                    # Other tracks: their query already defines the course.
                    if slug == "aml-kyc":
                        if not aml_gate(r.get("title"), r.get("snippet")):
                            continue
                    elif not relevant(r, keywords):
                        continue
                    key = (norm(r.get("title")), norm(r.get("company")))
                    if key in seen:
                        continue
                    seen.add(key)
                    jobs.append({
                        "id": "jb_" + str(r.get("id", ""))[:40],
                        "course": slug,
                        "course_label": label,
                        "title": (r.get("title") or "").strip(),
                        "company": (r.get("company") or "").strip(),
                        "location": (r.get("location") or "India").strip(),
                        "created": r.get("updated"),
                        "contract": (r.get("type") or "").lower(),
                        "snippet": clean(r.get("snippet")),
                        "url": r.get("link"),
                        "direct_url": r.get("link"),
                        "resolved": True,
                        "source": "jooble",
                        "publisher": r.get("source"),
                        "salary_text": (r.get("salary") or "").strip(),
                    })
                    track_added += 1
                time.sleep(0.5)
            time.sleep(0.5)
        added += track_added
        print(f"[ok] {label}: {track_added} new jobs")

    data["fetched_at"] = time.strftime("%Y-%m-%d")
    data["total"] = len(jobs)
    with open(JOBS_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"Merged {added} Jooble jobs. Board total: {len(jobs)}.")


if __name__ == "__main__":
    main()
