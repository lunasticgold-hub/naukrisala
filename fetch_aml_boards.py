#!/usr/bin/env python3
"""Fetch AML/KYC-relevant jobs from newly verified employer boards.

Boards: aml_boards.json (verified 2026-10-24: Greenhouse/Lever/Ashby/
Teamtailor public feeds, Workday CXS keyword searches, Pinpoint RSS).
Rules (hard, per user 2026-10-24):
  - ONLY jobs directly related to AML/KYC merge. The aml_gate() check in
    fetch_ats.py is applied to every candidate — no gate pass, no merge.
  - Location: India OR Remote/global (remote roles pass only via the gate).
  - Course is always aml-kyc; other tracks are out of scope here.
Merges into jobs.json, deduped by normalized (title, company).
"""
import json
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_ats import INDIA_RE, TRACK_LABELS, aml_gate, norm
from fetch_ats import board_jobs as ats_board_jobs
from fetch_ats2 import board_jobs as ats2_board_jobs
from fetch_enterprise import post_json

SITE = os.path.dirname(os.path.abspath(__file__))
JOBS_PATH = os.path.join(SITE, "jobs.json")
BOARDS_PATH = os.path.join(SITE, "aml_boards.json")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

REMOTE_RE = re.compile(
    r"remote|work from home|work-from-home|\bwfh\b|anywhere|distributed|"
    r"\bglobal\b|virtual|location independent",
    re.I,
)
HUBS_RE = re.compile(
    r"london|new york|singapore|dubai|dublin|amsterdam|berlin|toronto|"
    r"sydney|manila|kuala lumpur|warsaw|bucharest|lisbon|zurich",
    re.I,
)


def loc_ok(loc):
    loc = loc or ""
    return bool(INDIA_RE.search(loc) or REMOTE_RE.search(loc))


def workday_aml_jobs(host, tenant, site):
    """Workday CXS keyword searches (AML/KYC/sanctions/financial crime).

    The CXS list response carries no full description, so the gate runs on
    title + bulletFields snippets; context-only adjacent roles fail closed.
    """
    out, seen = [], set()
    for q in ["AML", "KYC", "sanctions", "financial crime"]:
        offset = 0
        for _ in range(60):
            try:
                d = post_json(f"https://{host}/wday/cxs/{tenant}/{site}/jobs",
                              {"appliedFacets": {}, "limit": 20,
                               "offset": offset, "searchText": q})
            except Exception as e:  # noqa: BLE001
                print(f"[workday] {host} q={q}: {e}", file=sys.stderr)
                break
            posts = d.get("jobPostings", [])
            if not posts:
                break
            for p in posts:
                ep = p.get("externalPath") or ""
                url = f"https://{host}/{site}{ep}"
                if url in seen:
                    continue
                seen.add(url)
                bullets = " ".join(str(b) for b in
                                   (p.get("bulletFields") or []))
                out.append({"title": p.get("title"),
                            "location": p.get("locationsText") or "",
                            "url": url, "desc": bullets})
            offset += 20
            if d.get("total") and offset >= d["total"]:
                break
            time.sleep(0.5)
    return out


def pinpoint_jobs(feed_url):
    req = urllib.request.Request(feed_url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as r:
        root = ET.fromstring(r.read())
    out = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        desc = re.sub(r"<[^>]+>", " ",
                      it.findtext("description") or "")[:2000]
        loc = ""
        for tag in ("location", "coverage"):
            v = it.findtext(tag)
            if v:
                loc = v.strip()
                break
        if not loc:
            # detail page: prefer structured jobLocation data; fall back to
            # a "Location" label; never guess from boilerplate prose.
            try:
                req2 = urllib.request.Request(link, headers=UA)
                with urllib.request.urlopen(req2, timeout=30) as r2:
                    html = r2.read().decode("utf-8", "replace")
                m = (re.search(r'"addressLocality"\s*:\s*"([^"]+)"', html)
                     or re.search(r'"jobLocation"[^}]{0,300}?"name"\s*:\s*"([^"]+)"',
                                  html)
                     or re.search(r"Location\s*</[^>]+>\s*<[^>]+>\s*([^<]{2,60})",
                                  html))
                loc = m.group(1).strip() if m else ""
            except Exception:  # noqa: BLE001
                loc = ""
        out.append({"title": title, "location": loc, "url": link,
                    "desc": desc})
    return out


def main():
    boards = json.load(open(BOARDS_PATH))
    with open(JOBS_PATH) as f:
        data = json.load(f)
    jobs = data["jobs"]
    seen = {(norm(j.get("title")), norm(j.get("company"))) for j in jobs}

    added_total = 0
    for b in boards:
        company = b["company"]
        try:
            if "ats" in b:
                fn = (ats_board_jobs if b["ats"] in
                      ("greenhouse", "lever", "ashby") else ats2_board_jobs)
                postings = fn(b)
            elif b.get("platform") == "workday":
                p = b["params"]
                postings = workday_aml_jobs(p["host"], p["tenant"],
                                            p["site"])
            elif b.get("platform") == "pinpoint-rss":
                postings = pinpoint_jobs(b["params"]["feed"])
            else:
                print(f"[skip] {company}: unknown board shape",
                      file=sys.stderr)
                continue
        except Exception as e:  # noqa: BLE001
            print(f"[skip] {company}: {e}", file=sys.stderr)
            continue
        kept = 0
        for p in postings:
            if not p.get("url") or not p.get("title"):
                continue
            if not loc_ok(p.get("location")):
                continue
            if not aml_gate(p["title"], p.get("desc") or ""):
                continue
            key = (norm(p["title"]), norm(company))
            if key in seen:
                continue
            seen.add(key)
            uid = re.sub(r"\D", "", p["url"])[-10:] or \
                str(abs(hash(key)))[-10:]
            jobs.append({
                "id": "aml_" + uid,
                "course": "aml-kyc",
                "course_label": TRACK_LABELS["aml-kyc"],
                "title": p["title"],
                "company": company,
                "location": p.get("location", ""),
                "created": None,
                "contract": "",
                "snippet": (p.get("desc") or "")[:280],
                "url": p["url"],
                "direct_url": p["url"],
                "resolved": True,
                "source": "aml-boards",
                "publisher": company + " careers",
                "posted": p.get("posted", ""),
            })
            kept += 1
        added_total += kept
        print(f"[ok] {company}: {kept} added ({len(postings)} postings)")
        time.sleep(0.4)
    data["fetched_at"] = time.strftime("%Y-%m-%d")
    data["total"] = len(jobs)
    with open(JOBS_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"Merged {added_total} AML-board jobs. Board total: {len(jobs)}.")


if __name__ == "__main__":
    main()
