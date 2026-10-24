#!/usr/bin/env python3
"""Discover how a career page serves its jobs, so it can be added to
browser_boards.json WITHOUT guessing URLs.

Given a careers-page URL it:
  1) fetches the page HTML and detects ATS markers (greenhouse, lever,
     ashby, workday, smartrecruiters, eightfold, oracle, successfactors,
     taleo, phenom, ripplehire, darwinbox, keka, workable, recruitee,
     personio, breezy, teamtailor, pinpoint),
  2) for ATS platforms with a known public API, PROBES that API live and
     reports the job count + a ready-to-paste board entry,
  3) for custom portals, extracts candidate API endpoints from the page
     source and reports them for a browser-tool inspection.

Usage: python3 discover_board.py <careers-page-URL> [Company Name]
Prints a JSON report; also saves discover_report.json next to the script.
"""
import json
import os
import re
import sys
import urllib.request
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 Chrome/124 Safari/537.36"}

MARKERS = {
    "greenhouse": ["greenhouse", "boards.greenhouse.io"],
    "lever": ["lever.co", "jobs.lever.co"],
    "ashby": ["ashbyhq"],
    "workday": ["myworkdayjobs", "workday"],
    "smartrecruiters": ["smartrecruiters"],
    "eightfold": ["eightfold"],
    "oracle": ["oraclecloud", "recruitingCE"],
    "successfactors": ["successfactors", "sapsf"],
    "taleo": ["taleo"],
    "phenom": ["phenom"],
    "ripplehire": ["ripplehire"],
    "darwinbox": ["darwinbox"],
    "keka": ["keka"],
    "workable": ["workable"],
    "recruitee": ["recruitee"],
    "personio": ["personio"],
    "breezy": ["breezy"],
    "teamtailor": ["teamtailor"],
    "pinpoint": ["pinpoint"],
}


def fetch_text(url, timeout=45):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def fetch_json(url, timeout=45):
    return json.loads(fetch_text(url, timeout))


def probe_greenhouse(html, url):
    m = (re.search(r"boards\.greenhouse\.io/([a-z0-9\-]+)", html + " " + url)
         or re.search(r"boards-api\.greenhouse\.io/v1/boards/([a-z0-9\-]+)",
                      html))
    if not m:
        return None
    slug = m.group(1)
    try:
        d = fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
        jobs = d.get("jobs", [])
        return {"engine": "greenhouse", "params": {"slug": slug},
                "sample_jobs": len(jobs),
                "sample_title": (jobs[0].get("title") if jobs else None)}
    except Exception as e:  # noqa: BLE001
        return {"engine": "greenhouse", "params": {"slug": slug},
                "error": str(e)}


def probe_lever(html, url):
    m = re.search(r"jobs\.lever\.co/([a-z0-9\-]+)", html + " " + url)
    if not m:
        return None
    slug = m.group(1)
    try:
        d = fetch_json(f"https://api.lever.co/v0/postings/{slug}?mode=json")
        return {"engine": "lever", "params": {"slug": slug},
                "sample_jobs": len(d) if isinstance(d, list) else 0,
                "sample_title": (d[0].get("text") if isinstance(d, list)
                                 and d else None)}
    except Exception as e:  # noqa: BLE001
        return {"engine": "lever", "params": {"slug": slug}, "error": str(e)}


def probe_ashby(html, url):
    m = re.search(r"jobs\.ashbyhq\.com/([a-z0-9\-]+)", html + " " + url)
    if not m:
        return None
    slug = m.group(1)
    try:
        d = fetch_json("https://api.ashbyhq.com/posting-api/job-board/"
                       f"{slug}?includeCompensation=true")
        jobs = d.get("jobs", [])
        return {"engine": "ashby", "params": {"slug": slug},
                "sample_jobs": len(jobs),
                "sample_title": (jobs[0].get("title") if jobs else None)}
    except Exception as e:  # noqa: BLE001
        return {"engine": "ashby", "params": {"slug": slug}, "error": str(e)}


def probe_workday(html, url):
    m = re.search(r"([a-z0-9\-]+\.wd\d\.myworkdayjobs\.com)/([a-z0-9\-_]+)",
                  html + " " + url)
    if not m:
        return None
    host, site = m.group(1), m.group(2)
    # tenant is derivable only from the CXS path; probe the standard one:
    # the site segment after /wday/cxs/ is the tenant, usually the host
    # prefix. Try host-prefix tenant first.
    tenant = host.split(".")[0]
    try:
        from fetch_enterprise import post_json
        d = post_json(f"https://{host}/wday/cxs/{tenant}/{site}/jobs",
                      {"appliedFacets": {}, "limit": 1, "offset": 0,
                       "searchText": "AML"})
        total = d.get("total", len(d.get("jobPostings", [])))
        return {"engine": "workday",
                "params": {"host": host, "tenant": tenant, "site": site},
                "sample_jobs": total,
                "note": "count is AML-keyword search; verify tenant if 0"}
    except Exception as e:  # noqa: BLE001
        return {"engine": "workday",
                "params": {"host": host, "tenant": tenant, "site": site},
                "error": str(e)}


def probe_smartrecruiters(html, url):
    m = re.search(r"jobs\.smartrecruiters\.com/([a-z0-9\-]+)", html + " " + url)
    if not m:
        return None
    slug = m.group(1)
    try:
        d = fetch_json("https://api.smartrecruiters.com/v1/companies/"
                       f"{slug}/postings?limit=1")
        return {"engine": "smartrecruiters", "params": {"slug": slug},
                "sample_jobs": d.get("totalFound", len(d.get("content", [])))}
    except Exception as e:  # noqa: BLE001
        return {"engine": "smartrecruiters", "params": {"slug": slug},
                "error": str(e)}


def probe_eightfold(html, url):
    m = re.search(r"([a-z0-9\-]+)\.eightfold\.ai", html + " " + url)
    if not m:
        return None
    slug = m.group(1)
    try:
        d = fetch_json(f"https://{slug}.eightfold.ai/api/apply/v2/jobs")
        return {"engine": "eightfold", "params": {"slug": slug},
                "sample_jobs": d.get("total", len(d.get("jobs", [])))}
    except Exception as e:  # noqa: BLE001
        return {"engine": "eightfold", "params": {"slug": slug},
                "error": str(e)}


def main():
    if len(sys.argv) < 2:
        print("usage: discover_board.py <careers-page-URL> [Company Name]")
        sys.exit(2)
    url, company = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "")
    report = {"url": url, "company": company, "detected": [],
              "probes": [], "candidate_api_urls": [], "verdict": ""}
    try:
        html = fetch_text(url)
    except Exception as e:  # noqa: BLE001
        report["verdict"] = f"page fetch failed: {e} — retry or inspect in browser"
        print(json.dumps(report, indent=2))
        return
    low = html.lower()
    for name, needles in MARKERS.items():
        if any(n in low or n in url.lower() for n in needles):
            report["detected"].append(name)
    probes = {"greenhouse": probe_greenhouse, "lever": probe_lever,
              "ashby": probe_ashby, "workday": probe_workday,
              "smartrecruiters": probe_smartrecruiters,
              "eightfold": probe_eightfold}
    for name in report["detected"]:
        if name in probes:
            try:
                report["probes"].append(probes[name](html, url))
            except Exception as e:  # noqa: BLE001
                report["probes"].append({"engine": name, "error": str(e)})
    # candidate API endpoints embedded in the page source
    apis = set(re.findall(r"https?://[a-z0-9\-./_~:?#@!$&'()*+,;=%]+api[a-z0-9\-./_~:?#@!$&'()*+,;=%]*", html, re.I))
    report["candidate_api_urls"] = sorted(apis)[:20]
    ok = [p for p in report["probes"] if p.get("sample_jobs")]
    if ok:
        p = ok[0]
        report["verdict"] = "READY — add to browser_boards.json:"
        report["suggested_entry"] = {
            "company": company or "TODO: company name",
            "careers_url": url, "engine": p["engine"], "params": p["params"]}
    elif report["detected"]:
        report["verdict"] = ("ATS detected but no public API probe succeeded — "
                             "needs a live-browser inspection to find the "
                             "XHR endpoint, then add as generic_json.")
    else:
        report["verdict"] = ("No known ATS detected — custom portal. Check "
                             "candidate_api_urls, else inspect in a live "
                             "browser (Network tab) for the jobs XHR call.")
    print(json.dumps(report, indent=2))
    with open(os.path.join(SITE, "discover_report.json"), "w") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
