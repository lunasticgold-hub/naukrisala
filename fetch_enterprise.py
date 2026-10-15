#!/usr/bin/env python3
"""Fetch India jobs from enterprise ATS public APIs (round 3).

Platforms (all keyless, official endpoints the career sites themselves load):
  - Oracle Recruiting Cloud (banks/enterprises)
  - Workday CXS (large employers: Intel, Visa, Mastercard, PayPal, ...)
  - Eightfold (HSBC, Bayer)
  - SmartRecruiters documented public API (Altisource, EJOBS, Avery Dennison)

Board list: enterprise_boards.json (verified endpoints with India presence).
Apply links are employer career-site URLs — zero intermediaries.
Classification is title-only (deliberately strict: avoids the description-match
false positives seen in the ATS round).
Merges into jobs.json, deduped by normalized (title, company).
"""
import json, os, re, sys, time, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_ats import TRACK_FILTERS, TRACK_LABELS, INDIA_RE, norm

SITE = os.path.dirname(os.path.abspath(__file__))
JOBS_PATH = os.path.join(SITE, "jobs.json")
BOARDS_PATH = os.path.join(SITE, "enterprise_boards.json")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def get_json(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def post_json(url, payload, timeout=60):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={**UA, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


# ---------- SmartRecruiters (documented public API) ----------

def sr_jobs(slug):
    out, offset, total = [], 0, None
    while True:
        d = get_json("https://api.smartrecruiters.com/v1/companies/"
                     f"{slug}/postings?limit=100&offset={offset}")
        content = d.get("content", [])
        total = d.get("totalFound", len(content))
        for p in content:
            loc = p.get("location") or {}
            loc_s = ", ".join(x for x in
                              [loc.get("city"), loc.get("country")] if x)
            # ref is an API URL; build the public job page URL instead
            pid = p.get("id")
            url = (f"https://jobs.smartrecruiters.com/{slug}/{pid}"
                   if pid else p.get("ref"))
            out.append({"title": p.get("name"), "location": loc_s,
                        "url": url, "country": loc.get("country")})
        offset += len(content)
        if not content or offset >= total or offset >= 1000:
            break
        time.sleep(0.3)
    return out


# ---------- Oracle Recruiting Cloud ----------

def oracle_jobs(host, site):
    num = re.sub(r"\D", "", site) or site
    out, offset, total = [], 0, None
    for _ in range(40):  # up to 8,000 reqs
        q = (f"?onlyData=true&expand=requisitionList.secondaryLocations"
             f"&finder=findReqs;siteNumber={num},limit=200,offset={offset}")
        d = get_json(f"https://{host}/hcmRestApi/resources/latest/"
                     f"recruitingCEJobRequisitions{q}")
        total = d.get("TotalJobsCount", 0)
        reqs = []
        for item in d.get("items", []):
            reqs.extend(item.get("requisitionList", []))
        if not reqs:
            # retry once with the raw site string (some tenants want CX_N)
            if num != site:
                num = site
                continue
            break
        for r in reqs:
            out.append({"title": r.get("Title"),
                        "location": r.get("PrimaryLocation") or "",
                        "country": r.get("PrimaryLocationCountry") or "",
                        "url": (f"https://{host}/hcmUI/CandidateExperience/en/"
                                f"sites/{site}/job/{r.get('Id')}"),
                        "posted": (r.get("PostedDate") or "")[:10]})
        offset += 200
        if offset >= total:
            break
        time.sleep(0.4)
    return out


# ---------- Workday CXS ----------

def workday_jobs(host, tenant, site):
    out, offset, total = [], 0, None
    for _ in range(16):  # up to 320 postings
        d = post_json(f"https://{host}/wday/cxs/{tenant}/{site}/jobs",
                      {"appliedFacets": {}, "limit": 20, "offset": offset,
                       "searchText": "India"})
        total = d.get("total", 0)
        posts = d.get("jobPostings", [])
        if not posts:
            break
        for p in posts:
            loc = p.get("locationsText") or ""
            if not INDIA_RE.search(loc):
                continue
            ep = p.get("externalPath") or ""
            posted = p.get("postedOn") or ""
            m = re.search(r"(\d+)\s+day", posted, re.I)
            if m:
                posted = time.strftime(
                    "%Y-%m-%d",
                    time.localtime(time.time() - int(m.group(1)) * 86400))
            out.append({"title": p.get("title"), "location": loc,
                        "url": f"https://{host}/{site}{ep}",
                        "posted": posted if re.match(r"\d{4}-\d\d-\d\d",
                                                     posted) else ""})
        offset += 20
        if offset >= total:
            break
        time.sleep(0.4)
    return out


# ---------- Eightfold (slow API: ~20s/response, 10/page) ----------

def _eightfold_page(args):
    slug, start = args
    try:
        d = get_json(f"https://{slug}.eightfold.ai/api/apply/v2/jobs"
                     f"?start={start}&num=100", timeout=120)
        return start, d.get("positions", []), d.get("count", 0)
    except Exception as e:  # noqa: BLE001
        print(f"[eightfold] page {start}: {e}", file=sys.stderr)
        return start, [], 0


def eightfold_jobs(slug):
    d0 = get_json(f"https://{slug}.eightfold.ai/api/apply/v2/jobs"
                  f"?start=0&num=100", timeout=120)
    positions = d0.get("positions", [])
    total = d0.get("count", 0)
    pagesize = len(positions) or 10
    starts = list(range(pagesize, total, pagesize))
    with ThreadPoolExecutor(max_workers=6) as ex:
        for _, page, _ in ex.map(_eightfold_page,
                                 [(slug, s) for s in starts]):
            positions.extend(page)
    out = []
    for p in positions:
        locs = p.get("locations") or []
        loc_s = "; ".join(
            ", ".join(str(v) for k, v in (l.items() if isinstance(l, dict)
                                          else [("loc", l)])
                      if k in ("city", "name", "country", "loc") and v)
            for l in locs)
        if not INDIA_RE.search(loc_s):
            continue
        out.append({"title": p.get("title") or p.get("name"),
                    "location": loc_s[:200],
                    "url": p.get("canonicalPositionUrl") or "",
                    "posted": ""})
    return out


PLATFORM_FETCH = {
    "smartrecruiters": lambda b: sr_jobs(b["params"]["slug"]),
    "oracle": lambda b: oracle_jobs(b["params"]["host"],
                                    b["params"]["site"]),
    "workday": lambda b: workday_jobs(b["params"]["host"],
                                      b["params"]["tenant"],
                                      b["params"]["site"]),
    "eightfold": lambda b: eightfold_jobs(b["params"]["slug"]),
}


def main():
    boards = json.load(open(BOARDS_PATH))
    with open(JOBS_PATH) as f:
        data = json.load(f)
    jobs = data["jobs"]
    seen = {(norm(j.get("title")), norm(j.get("company"))) for j in jobs}

    # resume support: pass a company-name prefix to skip earlier boards
    resume_after = sys.argv[1] if len(sys.argv) > 1 else ""
    skipping = bool(resume_after)
    added_total, per_track = 0, {s: 0 for s in TRACK_FILTERS}
    for b in boards:
        if skipping:
            if b["company"] == resume_after:
                skipping = False
            continue
        if b.get("india_jobs", 1) == 0:
            print(f"[skip] {b['company']}: no India jobs measured",
                  file=sys.stderr)
            continue
        try:
            postings = PLATFORM_FETCH[b["platform"]](b)
        except Exception as e:  # noqa: BLE001
            print(f"[skip] {b['company']}: {e}", file=sys.stderr)
            continue
        company = b["company"]
        kept = 0
        for p in postings:
            if not p.get("url") or not p.get("title"):
                continue
            if not INDIA_RE.search((p.get("location") or "") + " " +
                                   (p.get("country") or "")):
                continue
            hay = norm(str(p["title"]))
            matched = [s for s, kws in TRACK_FILTERS.items()
                       if any(k in hay for k in kws)]
            for slug in matched:
                key = (norm(p["title"]), norm(company))
                if key in seen:
                    continue
                seen.add(key)
                uid = re.sub(r"\D", "", p["url"])[-10:] or \
                    str(abs(hash(key)))[-10:]
                jobs.append({
                    "id": "ent_" + slug[:3] + "_" + uid,
                    "course": slug,
                    "course_label": TRACK_LABELS[slug],
                    "title": p["title"],
                    "company": company,
                    "location": p.get("location", ""),
                    "created": None,
                    "contract": "",
                    "snippet": "",
                    "url": p["url"],
                    "direct_url": p["url"],
                    "resolved": True,
                    "source": "enterprise",
                    "publisher": company + " careers",
                    "posted": p.get("posted", ""),
                })
                per_track[slug] += 1
                added_total += 1
                kept += 1
        print(f"[ok] {company}: {kept} added ({len(postings)} India postings)")
    data["fetched_at"] = time.strftime("%Y-%m-%d")
    data["total"] = len(jobs)
    with open(JOBS_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    print("Enterprise merge by track:",
          {k: v for k, v in per_track.items() if v})
    print(f"Merged {added_total} enterprise jobs. Board total: {len(jobs)}.")


if __name__ == "__main__":
    main()
