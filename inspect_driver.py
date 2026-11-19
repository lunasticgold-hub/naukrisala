#!/usr/bin/env python3
"""Phase-A deep-inspection driver for the career pages the first crawl
could NOT wire up. Read-only with respect to the board: writes ONLY
inspect_boards.json (verified entries) and inspect_progress.json
(one outcome per company). NEVER touches browser_boards.json, jobs.json,
or jobs.html — the other crawl worker is mid-merge.

Per company (sequential, polite sleeps):
  1. Dedupe against existing boards (normalized names + alias map).
  2. Find the REAL jobs page: sheet search_url, then careers_url, then
     /careers path on the same host, then careers links found on the
     homepage HTML (observed, never guessed API URLs).
  3. Fetch page + promising JS bundles; scan for ATS markers/API hosts.
  4. Known engines (workday/oracle/eightfold/smartrecruiters/greenhouse/
     lever/ashby/workable/recruitee/personio/breezy/teamtailor): verify
     with a live capped API call built ONLY from observed host/site/slug.
  5. New platforms (ripplehire/successfactors/phenom/darwinbox/...):
     test candidate endpoints observed in page/JS; on real jobs returned,
     build a generic_json entry and prove it via a temp-config dry-run
     of fetch_browser_boards.py before marking wired_ready.
  6. Otherwise: needs_browser with all evidence (Layer-2 input).

Usage:
  python3 inspect_driver.py --phase 1            # 22 needs_inspection
  python3 inspect_driver.py --phase 2            # big-name custom portals
  python3 inspect_driver.py --phase 3            # remaining tail, rank order
  python3 inspect_driver.py --only "HDFC Bank,Axis Bank"
  python3 inspect_driver.py --limit 10           # first 10 of the phase
Resumable: companies already in inspect_progress.json are skipped.
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.dirname(os.path.abspath(__file__))
PROG = os.path.join(SITE, "crawl_progress.json")
TARG = os.path.join(SITE, "crawl_targets.json")
OUT_BOARDS = os.path.join(SITE, "inspect_boards.json")
OUT_PROG = os.path.join(SITE, "inspect_progress.json")
TMP_CFG = "/tmp/inspect_test_boards.json"

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
      "image/avif,image/webp,*/*;q=0.8",
      "Accept-Language": "en-IN,en;q=0.9",
      "Accept-Encoding": "identity"}
MOBILE_UA = {"User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) "
             "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 "
             "Mobile Safari/537.36"}

MARKERS = {
    "ripplehire": ["ripplehire"], "successfactors": ["successfactors", "sapsf"],
    "taleo": ["taleo"], "phenom": ["phenom"], "oracle": ["oraclecloud"],
    "workday": ["myworkdayjobs"], "eightfold": ["eightfold"],
    "smartrecruiters": ["smartrecruiters"], "greenhouse": ["greenhouse"],
    "lever": ["lever.co"], "ashby": ["ashbyhq"], "workable": ["workable"],
    "recruitee": ["recruitee"], "personio": ["personio"],
    "breezy": ["breezy"], "teamtailor": ["teamtailor"],
    "darwinbox": ["darwinbox"], "keka": ["keka"], "pinpoint": ["pinpoint"],
    "jobvite": ["jobvite"], "icims": ["icims"], "avature": ["avature"],
    "brassring": ["brassring"],
}

# Manual aliases: crawl name -> existing board company name (same employer,
# different label in the sheet vs the board files).
ALIASES = {
    "kpmg": "kpmgindia", "bnybankofnewyorkmellon": "bny",
    "jpmorganchase": "jpmorgan",
}


def norm_name(s):
    n = re.sub(r"[^a-z0-9]", "", (s or "").lower())
    for suf in ("privatelimited", "limited", "ltd", "india", "indian",
                "company", "group", "holdings", "plc", "incorporated"):
        if n.endswith(suf) and len(n) - len(suf) >= 3:
            n = n[: -len(suf)]
    return n


def load_covered():
    covered = {}
    for f in ["ats_boards.json", "ats_boards2.json", "enterprise_boards.json",
              "aml_boards.json", "browser_boards.json"]:
        try:
            d = json.load(open(os.path.join(SITE, f)))
        except Exception:
            continue
        for b in d if isinstance(d, list) else d.get("boards", []):
            covered[norm_name(b.get("company", ""))] = (f, b.get("company"))
    return covered


def fetch(url, headers=UA, timeout=45):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace"), r.geturl()


def fetch_json(url, headers=UA, timeout=45, data=None):
    h = dict(headers)
    if data is not None:
        h["Content-Type"] = "application/json"
        body = json.dumps(data).encode()
    else:
        body = None
    req = urllib.request.Request(url, headers=h, data=body)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def js_urls(html, base):
    out = []
    for m in re.finditer(r"""src=["']([^"']+\.js[^"']*)["']""", html):
        u = urllib.parse.urljoin(base, m.group(1))
        if u not in out:
            out.append(u)
    return out


def detect(text):
    low = text.lower()
    return [k for k, needles in MARKERS.items()
            if any(n in low for n in needles)]


# ---------------- verification helpers (capped live calls) ----------------

def verify_workday(host, tenant, site):
    d = fetch_json(f"https://{host}/wday/cxs/{tenant}/{site}/jobs",
                   data={"appliedFacets": {}, "limit": 5, "offset": 0,
                         "searchText": ""})
    posts = d.get("jobPostings", [])
    if posts:
        return {"engine": "workday",
                "params": {"host": host, "tenant": tenant, "site": site},
                "sample_jobs": len(posts),
                "sample_title": posts[0].get("title")}
    return None


def verify_oracle(host, site):
    num = re.sub(r"\D", "", site) or site
    q = ("?onlyData=true&expand=requisitionList.secondaryLocations"
         f"&finder=findReqs;siteNumber={num},limit=10,offset=0")
    d = fetch_json(f"https://{host}/hcmRestApi/resources/latest/"
                   f"recruitingCEJobRequisitions{q}")
    reqs = []
    for item in d.get("items", []):
        reqs.extend(item.get("requisitionList", []))
    if reqs:
        return {"engine": "oracle", "params": {"host": host, "site": site},
                "sample_jobs": len(reqs),
                "sample_title": reqs[0].get("Title")}
    return None


def verify_eightfold(slug):
    d = fetch_json(f"https://{slug}.eightfold.ai/api/apply/v2/jobs")
    jobs = d.get("jobs", [])
    if jobs:
        return {"engine": "eightfold", "params": {"slug": slug},
                "sample_jobs": len(jobs),
                "sample_title": jobs[0].get("title") or jobs[0].get("name")}
    return None


def verify_smartrecruiters(slug):
    d = fetch_json("https://api.smartrecruiters.com/v1/companies/"
                   f"{slug}/postings?limit=1")
    if d.get("content"):
        return {"engine": "smartrecruiters", "params": {"slug": slug},
                "sample_jobs": d.get("totalFound", 1)}
    return None


def verify_simple_ats(engine, slug):
    """Single-call public APIs: greenhouse / lever / ashby."""
    try:
        if engine == "greenhouse":
            d = fetch_json("https://boards-api.greenhouse.io/v1/boards/"
                           f"{slug}/jobs")
            jobs = d.get("jobs", [])
        elif engine == "lever":
            d = fetch_json(f"https://api.lever.co/v0/postings/{slug}"
                           "?mode=json&limit=1")
            jobs = d if isinstance(d, list) else []
        elif engine == "ashby":
            d = fetch_json("https://api.ashbyhq.com/posting-api/job-board/"
                           f"{slug}?includeCompensation=true")
            jobs = d.get("jobs", [])
        else:
            return None
    except Exception:
        return None
    if jobs:
        t = jobs[0].get("title") or jobs[0].get("text")
        return {"engine": engine, "params": {"slug": slug},
                "sample_jobs": len(jobs), "sample_title": t}
    return None


def try_generic_endpoint(api_url, method="GET"):
    """GET a candidate endpoint; return (jobs_list, jobs_path) if it looks
    like real job data, else None. Only accepts shapes with title+url."""
    try:
        d = fetch_json(api_url) if method == "GET" else None
    except Exception:
        return None
    if not isinstance(d, dict):
        return None
    for path in ("jobs", "data", "data.jobs", "results", "items",
                 "content", "postings", "jobPostings", "requisitionList"):
        cur = d
        ok = True
        for part in path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok and isinstance(cur, list) and len(cur) >= 3:
            good = 0
            for j in cur[:10]:
                if isinstance(j, dict) and (j.get("title") or j.get("name")) \
                        and (j.get("url") or j.get("link") or j.get("id")):
                    good += 1
            if good >= 3:
                return cur, path
    return None


# ---------------- per-company processing ----------------

def page_candidates(t):
    urls = []
    for k in ("search_url", "careers_url"):
        u = (t.get(k) or "").strip()
        if u and u not in urls:
            urls.append(u)
    base = urls[0] if urls else ""
    if base:
        p = urllib.parse.urlparse(base)
        origin = f"{p.scheme}://{p.netloc}"
        for extra in ("/careers", "/careers/", "/jobs", "/en/careers"):
            u = origin + extra
            if u not in urls:
                urls.append(u)
    return urls


def process_company(company, t, covered, out_prog, out_boards):
    nn = norm_name(company)
    if nn in covered or ALIASES.get(nn) in covered:
        f, name = covered.get(nn) or covered.get(ALIASES.get(nn, ""), ("", ""))
        out_prog[company] = {"outcome": "already_covered",
                             "via": [f, name]}
        return
    tried, evidence = [], {}
    pages = []  # (url, html, final_url) — all successfully fetched pages
    for url in page_candidates(t):
        tried.append(url)
        html = ""
        for headers in (UA, MOBILE_UA):
            try:
                html, final_url = fetch(url, headers=headers)
                break
            except Exception as e:
                evidence.setdefault("fetch_errors", []).append(
                    f"{url}: {type(e).__name__}: {str(e)[:100]}")
                html = ""
        if html:
            pages.append((url, html, final_url))
            # Stop early ONLY if this page already shows a job system.
            # A homepage fetch "succeeding" must not end the search: the
            # real jobs page (e.g. /careers) is worth more than a fast
            # finish, and homepages carry no ATS markers.
            if detect(html):
                break
        time.sleep(0.4)
    if not pages:
        out_prog[company] = {"outcome": "failed",
                             "detail": {"tried": tried,
                                        "errors": evidence.get("fetch_errors", [])}}
        return
    # Follow careers links found on the first page (observed, not guessed)
    # and FETCH them — earlier code only listed them, never fetched.
    first_html, first_final = pages[0][1], pages[0][2]
    for m in re.finditer(r"""href=["']([^"']+)["']""", first_html):
        href = m.group(1)
        if re.search(r"career|job", href, re.I) and "://" in href \
                and not re.search(r"twitter|facebook|linkedin|youtube|instagram",
                                  href, re.I):
            full = urllib.parse.urljoin(first_final, href)
            if full not in tried and len(pages) < 6:
                tried.append(full)
                try:
                    html2, fin2 = fetch(full)
                    pages.append((full, html2, fin2))
                    if detect(html2):
                        break
                except Exception as e:
                    evidence.setdefault("fetch_errors", []).append(
                        f"{full}: {type(e).__name__}: {str(e)[:100]}")
                time.sleep(0.4)
    # Choose the page with a job system; else the first successful fetch.
    html_all, final_url = pages[0][1], pages[0][2]
    for _u, _h, _f in pages:
        if detect(_h):
            html_all, final_url = _h, _f
            break
    # fetch promising first-party JS bundles for API evidence
    js_text = ""
    for js in js_urls(html_all, final_url)[:12]:
        try:
            jt, _ = fetch(js, timeout=20)
            js_text += "\n" + jt[:200000]
        except Exception:
            pass
        time.sleep(0.3)
    combined = html_all + "\n" + js_text
    found = detect(combined)
    evidence = {"tried": tried, "final_url": final_url, "detected": found,
                "candidate_api_urls": sorted(set(re.findall(
                    r"https?://[a-z0-9\-./_~:?#@!$&'()*+,;=%]*api[a-z0-9\-./_~:?#@!$&'()*+,;=%]*",
                    combined, re.I)))[:15]}
    # --- known-engine verification from OBSERVED host/site/slug ---
    verified = None
    try:
        if "workday" in found:
            # Workday URLs carry an optional locale segment before the site:
            # host/en-US/SiteName or host/SiteName. Capture the site, not
            # the locale (previous bug captured "en" -> 404).
            m = re.search(r"([a-z0-9\-]+\.wd\d+\.myworkdayjobs\.com)/"
                          r"(?:[a-z]{2}-[A-Z]{2}/)?([A-Za-z0-9\-_]+)",
                          combined)
            if m:
                host, site = m.group(1), m.group(2)
                tenant = host.split(".")[0]
                verified = verify_workday(host, tenant, site)
        if not verified and "oracle" in found:
            m = re.search(r"([a-z0-9\-]+\.fa\.[a-z0-9\-]+\.oraclecloud\.com)",
                          combined)
            ms = re.search(r"/sites/(CX_[A-Za-z0-9_]+)", combined)
            if m and ms:
                verified = verify_oracle(m.group(1), ms.group(1))
        if not verified and "eightfold" in found:
            m = re.search(r"([a-z0-9\-]+)\.eightfold\.ai", combined)
            if m:
                verified = verify_eightfold(m.group(1))
        if not verified and "smartrecruiters" in found:
            m = re.search(r"jobs\.smartrecruiters\.com/([a-z0-9\-]+)", combined)
            if m:
                verified = verify_smartrecruiters(m.group(1))
        if not verified:
            for eng, pat in (
                    ("greenhouse", r"boards\.greenhouse\.io/([a-z0-9\-]+)"),
                    ("lever", r"jobs\.lever\.co/([a-z0-9\-]+)"),
                    ("ashby", r"jobs\.ashbyhq\.com/([a-z0-9\-]+)")):
                if eng in found:
                    m = re.search(pat, combined)
                    if m:
                        verified = verify_simple_ats(eng, m.group(1))
                        if verified:
                            break
    except Exception as e:
        evidence["verify_error"] = f"{type(e).__name__}: {str(e)[:150]}"
    if verified:
        entry = {"company": company, "careers_url": final_url,
                 "engine": verified["engine"], "params": verified["params"]}
        out_boards.append(entry)
        out_prog[company] = {"outcome": "wired_ready", "entry": entry,
                             "sample": {k: verified.get(k) for k in
                                        ("sample_jobs", "sample_title")},
                             "evidence": evidence}
        return
    # --- generic endpoint attempt (observed URLs only) ---
    for api_url in evidence["candidate_api_urls"]:
        if any(bad in api_url for bad in ("googleapis", "gstatic", "recaptcha",
                                          "facebook", "linkedin", "twitter",
                                          "fonts.", "maps.", "translate.")):
            continue
        got = try_generic_endpoint(api_url)
        if got:
            jobs, path = got
            j0 = jobs[0]
            title_k = "title" if "title" in j0 else "name"
            url_k = next((k for k in ("url", "link", "applyUrl", "jobUrl")
                          if k in j0), None)
            loc_k = next((k for k in ("location", "locationName", "city")
                          if k in j0), None)
            fields = {"title": title_k}
            if url_k:
                fields["url"] = url_k
            if loc_k:
                fields["location"] = loc_k
            entry = {"company": company, "careers_url": final_url,
                     "engine": "generic_json",
                     "params": {"api_url": api_url, "method": "GET",
                                "jobs_path": path, "fields": fields,
                                "pagination": {"kind": "none"}}}
            # prove it through the real fetcher on a TEMP config
            tmp = {"boards": [entry]}
            json.dump(tmp, open(TMP_CFG, "w"))
            env = dict(os.environ, BROWSER_BOARDS_JSON=TMP_CFG)
            r = subprocess.run([sys.executable, "fetch_browser_boards.py",
                                "--dry-run", "--board", company],
                               cwd=SITE, capture_output=True, text=True,
                               env=env, timeout=180)
            m = re.search(r"\[ok\] .*?: (\d+) added", r.stdout)
            if m and int(m.group(1)) > 0:
                out_boards.append(entry)
                out_prog[company] = {"outcome": "wired_ready", "entry": entry,
                                     "dry_run_added": int(m.group(1)),
                                     "evidence": evidence}
                return
            evidence.setdefault("generic_rejected", []).append(
                f"{api_url}: dry-run added 0 or failed: "
                f"{(r.stdout + r.stderr)[-200:]}")
    out_prog[company] = {"outcome": "needs_browser", "evidence": evidence}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", type=int, choices=[1, 2, 3])
    ap.add_argument("--only")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    targ = json.load(open(TARG))
    tmap = {t["company"]: t for t in targ}
    rank = [t["company"] for t in targ]

    # Phase 1 = the 22 needs_inspection companies from the first crawl
    # (detected platforms recorded then; re-probed fresh here).
    NEEDS_INSPECTION = [
        "HDFC Bank", "EY", "Axis Bank", "JPMorgan Chase",
        "Citigroup (Citi)", "Mphasis", "Bank of America",
        "BNY (Bank of New York Mellon)", "KPMG", "Sundaram Finance",
        "SMC Global Securities", "KreditBee", "Boston Consulting Group",
        "DTCC", "Shivalik Small Finance Bank", "Nasdaq",
        "Sundaram Mutual Fund (Sundaram Asset Management Company Limited)",
        "Invesco Mutual Fund (Invesco Asset Management (India) Private Limited)",
        "Citco", "FactSet",
        "PGIM India Mutual Fund (PGIM India Asset Management Private Limited)",
        "Acuity Knowledge Partners",
    ]
    BIG = ["State Bank of India", "ICICI Bank", "Kotak Mahindra Bank",
           "Punjab National Bank", "Bank of Baroda", "Bajaj Finserv",
           "Bajaj Finance", "Union Bank of India", "Indian Bank",
           "Canara Bank", "YES BANK", "RBL Bank", "IDFC FIRST Bank",
           "IndusInd Bank", "HDB Financial Services", "Shriram Finance",
           "L&T Finance", "Cholamandalam Investment and Finance",
           "Muthoot Finance", "Life Insurance Corporation of India",
           "SBI Life Insurance Company", "HDFC Life Insurance Company",
           "Aditya Birla Capital"]

    if args.only:
        todo = [c.strip() for c in args.only.split(",")]
    elif args.phase == 1:
        todo = [c for c in NEEDS_INSPECTION if c in tmap]
        todo = sorted(todo, key=lambda c: rank.index(c) if c in rank else 999)
    elif args.phase == 2:
        todo = [c for c in BIG if c in tmap]
    else:  # phase 3: everything else in rank order (fresh deep probe;
           # old triage is gone, so the driver classifies each itself)
        done = set()
        try:
            done = set(json.load(open(OUT_PROG)).keys())
        except Exception:
            pass
        skip = set(NEEDS_INSPECTION) | set(BIG)
        todo = [c for c in rank if c not in done and c not in skip]
    if args.limit:
        todo = todo[: args.limit]

    covered = load_covered()
    try:
        out_prog = json.load(open(OUT_PROG))
    except Exception:
        out_prog = {}
    try:
        out_boards = json.load(open(OUT_BOARDS))
    except Exception:
        out_boards = []
    have = {b["company"] for b in out_boards}

    for company in todo:
        if company in out_prog:  # resumable: skip done
            print(f"[skip] {company} (already in inspect_progress)")
            continue
        t = tmap.get(company, {"company": company})
        try:
            before = len(out_boards)
            process_company(company, t, covered, out_prog, out_boards)
            print(f"[{out_prog[company]['outcome']}] {company}")
        except Exception as e:
            out_prog[company] = {"outcome": "failed",
                                 "detail": f"driver error: {type(e).__name__}: {str(e)[:200]}"}
            print(f"[failed] {company}: {e}")
        json.dump(out_prog, open(OUT_PROG, "w"), ensure_ascii=False, indent=1)
        json.dump(out_boards, open(OUT_BOARDS, "w"), ensure_ascii=False, indent=1)
        time.sleep(0.5)
    print(f"DONE: {len(out_prog)} in inspect_progress, "
          f"{len(out_boards)} wired_ready boards.")


if __name__ == "__main__":
    main()
