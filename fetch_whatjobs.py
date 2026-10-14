#!/usr/bin/env python3
"""Fetch India jobs per NaukriSala course via WhatJobs Publisher FeedAPI.

Publisher ID 7372 (NaukriSala). Free publisher feed, no quota published.
Merges into jobs.json, deduped by normalized (title, company).
Filters obvious gig/AI-training spam (WhatJobs India feed is polluted with it).
"""
import json, re, sys, time, urllib.request, urllib.parse

PUBLISHER = "7372"
BASE = "https://api.whatjobs.com/api/v1/jobs.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

# (slug, label, [keyword queries], [categories], filter keywords or None)
TRACKS = [
    ("aml-kyc", "AML & KYC Analyst",
     ['"KYC analyst"', '"AML analyst"', "compliance", '"financial crime"',
      '"transaction monitoring"', '"due diligence"', "fraud", "sanctions"],
     ["finance", "banking"],
     ["aml", "kyc", "know your customer", "anti-money", "anti money",
      "compliance", "financial crime", "transaction monitoring",
      "due diligence", "sanctions", "fraud", "risk"]),
    ("servicenow", "ServiceNow Developer", ["ServiceNow"], ["it"], ["servicenow"]),
    ("data-science-ai", "Data Science & AI Engineering",
     ['"data scientist"', '"machine learning"'], ["it"],
     ["data scientist", "machine learning", "ml engineer", "ai engineer", "deep learning"]),
    ("stom", "STOM — Service Transition & Ops", ['"service management"'], ["it"],
     ["service management", "itsm", "itil", "service transition"]),
    ("power-bi", "Power BI Developer", ['"Power BI"'], ["it"], ["power bi", "powerbi"]),
    ("data-analyst", "Data Analyst", ['"data analyst"'], ["it"],
     ["data analyst", "data analytics"]),
    ("workday", "Workday Consultant", ["Workday"], ["it"], ["workday"]),
    ("python-fullstack", "Full Stack Python", ['"Python developer"'], ["it"],
     ["python", "django", "flask", "fastapi"]),
    ("java-fullstack", "Full Stack Java Developer", ['"Java developer"'], ["it"],
     ["java", "spring"]),
    ("qa-testing", "Software Testing (QA)", ['"QA engineer"', '"software tester"'], ["it"],
     ["qa", "quality assurance", "software test", "sdet", "test engineer", "tester"]),
    ("ib-operations", "Investment Banking Operations",
     ['"investment banking"'], ["finance", "banking"],
     ["investment banking", "ib operations", "trade settlement", "corporate actions"]),
    ("sap-fico", "SAP FICO (S/4HANA Finance)", ['"SAP FICO"'], ["it"],
     ["sap fico", "s/4hana finance", "sap finance"]),
    ("web-dev", "Web Development", ['"web developer"'], ["it"],
     ["web developer", "frontend", "front-end", "react", "angular", "vue"]),
    ("dotnet", ".NET Developer", ['".NET developer"'], ["it"],
     [".net", "dotnet", "c#", "asp.net"]),
    ("dbi", "Database & Business Intelligence",
     ['"business intelligence"'], ["it"],
     ["business intelligence", " bi ", "bi developer", "etl", "data warehouse"]),
]

# Obvious gig/AI-training spam signals in WhatJobs titles
SPAM_RES = [
    r"\$\s?\d+\s?/\s?hr", r"per task", r"upto\s?\$", r"up to\s?\$",
    r"benchmark specialist", r"scenario designer", r"ai collaboration",
    r"expert evaluator", r"domain expert evaluator",
    r"ai evaluation", r"\bevaluator\b", r"phd\b.*specialist", r"specialist.*\bphd\b",
]
SPAM_RE = re.compile("|".join(SPAM_RES), re.I)

SITE = __import__("os").path.dirname(__import__("os").path.abspath(__file__))
JOBS_PATH = SITE + "/jobs.json"


def norm(s):
    return re.sub(r"\s+", " ", (s or "").lower().strip())


def fetch(params):
    p = {"publisher": PUBLISHER, "user_ip": "87.81.231.44",
         "user_agent": UA, "limit": "100"}
    p.update(params)
    url = BASE + "?" + urllib.parse.urlencode(p)
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def clean_snippet(html, n=280):
    t = re.sub(r"<[^>]+>", " ", html or "")
    t = re.sub(r"\s+", " ", t).strip()
    return t[:n] + ("…" if len(t) > n else "")


def company_of(job):
    # WhatJobs JSON has no company field; try to mine from snippet/title
    return ""


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
    for slug, label, keywords, cats, kfilter in TRACKS:
        track_added = 0
        queries = [("keyword", k) for k in keywords]
        queries += [("category", c) for c in cats]
        for param, val in queries:
            page = 1
            while page <= 10:
                try:
                    d = fetch({param: val, "country": "in", "page": str(page),
                               "sort_by": "date"})
                except Exception as e:  # noqa: BLE001
                    print(f"[skip] {label} / {val} p{page}: {e}", file=sys.stderr)
                    break
                items = d.get("data") or []
                if not items:
                    break
                for it in items:
                    title = it.get("title") or ""
                    if SPAM_RE.search(title):
                        continue
                    if not relevant(it, kfilter):
                        continue
                    url = it.get("url") or ""
                    if not url:
                        continue
                    key = (norm(title), "")
                    if key in seen:
                        continue
                    seen.add(key)
                    jobs.append({
                        "id": "wj_" + re.sub(r"\D", "", url)[-12:],
                        "course": slug,
                        "course_label": label,
                        "title": title,
                        "company": "",
                        "location": it.get("location") or "India",
                        "created": None,
                        "contract": "",
                        "snippet": clean_snippet(it.get("snippet")),
                        "url": url,
                        "direct_url": url,
                        "resolved": False,
                        "source": "whatjobs",
                        "publisher": "WhatJobs",
                        "posted": "",
                    })
                    track_added += 1
                if len(items) < 100:
                    break
                page += 1
                time.sleep(0.5)
            time.sleep(0.4)
        added += track_added
        print(f"[ok] {label}: {track_added} new jobs")
    data["fetched_at"] = time.strftime("%Y-%m-%d")
    data["total"] = len(jobs)
    with open(JOBS_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"Merged {added} WhatJobs jobs. Board total: {len(jobs)}.")


if __name__ == "__main__":
    main()
