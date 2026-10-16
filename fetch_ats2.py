#!/usr/bin/env python3
"""Fetch India jobs per NaukriSala course from 5 more public ATS job-board APIs.

Sources: Workable / Recruitee / Personio / Breezy HR / Teamtailor public feeds
(keyless, unlimited). Board list: ats_boards2.json (verified slugs with India
presence). Apply links are the employer's own board URLs — zero intermediaries.
Merges into jobs.json, deduped by normalized (title, company).

Endpoint shapes (all verified live, no auth):
- Workable:   GET https://www.workable.com/api/accounts/{slug}?details=true
- Recruitee:   GET https://{slug}.recruitee.com/api/offers/
- Personio:    GET https://{slug}.jobs.personio.de/xml          (XML feed)
- Breezy HR:   GET https://{slug}.breezy.hr/json
- Teamtailor:  GET https://{slug}.teamtailor.com/jobs.json       (JSON Feed 1.1)
"""
import html as htmlmod
import json
import os
import re
import sys
import time
import urllib.request

from fetch_ats import INDIA_RE, TRACK_FILTERS, TRACK_LABELS, get, is_india, norm

SITE = os.path.dirname(os.path.abspath(__file__))
JOBS_PATH = os.path.join(SITE, "jobs.json")
BOARDS_PATH = os.path.join(SITE, "ats_boards2.json")


def get_text(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def clean(desc):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", desc or "")).strip()


def job_id(url):
    digs = re.sub(r"\D", "", url or "")
    if digs:
        return "ats2_" + digs[-10:]
    return "ats2_" + ("%08x" % (abs(hash(url or "")) % 16 ** 8))


def board_jobs(board):
    ats, slug = board["ats"], board["slug"]
    if ats == "workable":
        d = get(f"https://www.workable.com/api/accounts/{slug}?details=true")
        out = []
        for j in d.get("jobs", []):
            parts = []
            for loc in j.get("locations") or []:
                if isinstance(loc, dict):
                    parts.append(" ".join(str(loc.get(k) or "") for k in
                                          ("city", "region", "country") if loc.get(k)))
                elif loc:
                    parts.append(str(loc))
            loc = ", ".join(p for p in parts if p.strip())
            if not loc:
                loc = " ".join(str(j.get(k) or "") for k in ("city", "country")).strip()
            out.append({"title": j.get("title"), "location": loc,
                        "url": j.get("application_url") or j.get("url"),
                        "desc": clean(j.get("description"))[:2000],
                        "posted": (j.get("published_on") or "")[:10],
                        "contract": j.get("employment_type") or ""})
        return out
    if ats == "recruitee":
        d = get(f"https://{slug}.recruitee.com/api/offers/")
        out = []
        for o in d.get("offers", []):
            loc = (o.get("location") or "").strip()
            if not loc:
                loc = " ".join(str(o.get(k) or "") for k in ("city", "country")).strip()
            sal = o.get("salary") or {}
            out.append({"title": o.get("title"), "location": loc,
                        "url": o.get("careers_apply_url"),
                        "desc": clean(o.get("description"))[:2000],
                        "posted": (o.get("published_at") or "")[:10],
                        "contract": o.get("employment_type_code") or "",
                        "salary_min": sal.get("min"), "salary_max": sal.get("max"),
                        "salary_currency": sal.get("currency") or "INR",
                        "salary_period": sal.get("period") or ""})
        return out
    if ats == "personio":
        raw = get_text(f"https://{slug}.jobs.personio.de/xml")
        out = []
        for m in re.finditer(r"<position>(.*?)</position>", raw, re.S):
            blk = m.group(1)

            def tag(nm):
                mm = re.search(r"<%s>(.*?)</%s>" % (nm, nm), blk, re.S)
                return (mm.group(1).strip() if mm else "")

            pid = tag("id")
            descs = re.findall(r"<value>\s*<!\[CDATA\[(.*?)\]\]>\s*</value>", blk, re.S)
            url = f"https://{slug}.jobs.personio.de/job/{pid}" if pid else ""
            out.append({"title": htmlmod.unescape(tag("name")),
                        "location": htmlmod.unescape(tag("office")),
                        "url": url,
                        "desc": clean(" ".join(descs))[:2000],
                        "posted": "", "contract": ""})
        return out
    if ats == "breezy":
        d = get(f"https://{slug}.breezy.hr/json")
        out = []
        for j in d if isinstance(d, list) else []:
            locs = j.get("locations") or ([j.get("location")] if j.get("location") else [])
            parts = []
            for loc in locs:
                if isinstance(loc, dict):
                    nm = loc.get("name") or ""
                    ctry = (loc.get("country") or {}).get("name", "")
                    s = f"{nm} {ctry}".strip()
                    if s:
                        parts.append(s)
            typ = j.get("type") or {}
            out.append({"title": j.get("name"),
                        "location": ", ".join(parts),
                        "url": j.get("url"),
                        "desc": "",  # Breezy list feed carries no descriptions
                        "posted": (j.get("published_date") or "")[:10],
                        "contract": typ.get("name") if isinstance(typ, dict) else ""})
        return out
    if ats == "teamtailor":
        d = get(f"https://{slug}.teamtailor.com/jobs.json")
        out = []
        for it in d.get("items", []):
            jp = it.get("_jobposting") or {}
            parts = []
            for loc in jp.get("jobLocation") or []:
                addr = (loc or {}).get("address") or {}
                s = " ".join(str(addr.get(k) or "") for k in
                             ("addressLocality", "addressRegion", "addressCountry")).strip()
                if s:
                    parts.append(s)
            comp = ((jp.get("hiringOrganization") or {}).get("name")
                    or board["company"])
            out.append({"title": it.get("title"),
                        "location": ", ".join(parts),
                        "url": it.get("url"),
                        "desc": clean(it.get("content_html"))[:2000],
                        "posted": (it.get("date_published") or jp.get("datePosted") or "")[:10],
                        "contract": "", "company": comp})
        return out
    return []


def main():
    boards = json.load(open(BOARDS_PATH))
    with open(JOBS_PATH) as f:
        data = json.load(f)
    jobs = data["jobs"]
    seen = {(norm(j.get("title")), norm(j.get("company"))) for j in jobs}

    added_total, per_track = 0, {s: 0 for s in TRACK_FILTERS}
    for b in boards:
        try:
            postings = board_jobs(b)
        except Exception as e:  # noqa: BLE001
            print(f"[skip] {b['company']}: {e}", file=sys.stderr)
            continue
        company = b["company"]
        for p in postings:
            if not p["url"] or not is_india(p["location"]):
                continue
            hay = norm(str(p["title"]) + " " + p["desc"])
            matched = [s for s, kws in TRACK_FILTERS.items()
                       if any(k in hay for k in kws)]
            for slug in matched:
                comp = p.get("company") or company
                key = (norm(p["title"]), norm(comp))
                if key in seen:
                    continue
                seen.add(key)
                rec = {
                    "id": job_id(p["url"]),
                    "course": slug,
                    "course_label": TRACK_LABELS[slug],
                    "title": p["title"],
                    "company": comp,
                    "location": p["location"],
                    "created": p.get("posted") or None,
                    "contract": p.get("contract") or "",
                    "snippet": p["desc"][:280],
                    "url": p["url"],
                    "direct_url": p["url"],
                    "resolved": True,
                    "source": "ats2",
                    "publisher": comp + " careers",
                    "posted": "",
                }
                if p.get("salary_min") is not None or p.get("salary_max") is not None:
                    rec["salary_min"] = p.get("salary_min")
                    rec["salary_max"] = p.get("salary_max")
                    rec["salary_currency"] = p.get("salary_currency") or "INR"
                    rec["salary_period"] = p.get("salary_period") or ""
                jobs.append(rec)
                per_track[slug] += 1
                added_total += 1
        time.sleep(0.4)
    data["fetched_at"] = time.strftime("%Y-%m-%d")
    data["total"] = len(jobs)
    with open(JOBS_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    print("ATS2 merge by track:", {k: v for k, v in per_track.items() if v})
    print(f"Merged {added_total} ATS2 jobs. Board total: {len(jobs)}.")


if __name__ == "__main__":
    main()
