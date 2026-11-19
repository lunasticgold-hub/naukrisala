#!/usr/bin/env python3
"""board_scout.py — local, cheap career-page scout for the NaukriSala board.

Replaces per-company live-browser inspections (slow, credit-heavy) with
plain HTTP fetches + platform-pattern derivation. No browser, no logins,
no jobs.json writes, no secrets. A new board derived here only joins the
daily scan's config; it proves itself in the next daily run's own
per-board report (failures are isolated per board there, and a board
yielding 0 or erroring gets reviewed, not silently kept).

What it does per company (from crawl_targets.json, skipping anything
already wired in browser_boards.json or settled in inspect_progress.json
as already-covered/failed):
  - fetch the careers page (urllib, 25s timeout, <=1.5MB)
  - match the final URL + page links against proven platform patterns
    and derive the engine config (host/site/slug) for: ripplehire,
    oracle, peoplestrong, workday, greenhouse, lever, ashby, workable,
    recruitee
  - Darwinbox tenants are NOT probed: 4/4 live checks in Oct 2026
    (Sundaram Finance, AU Small Finance Bank, Piramal Finance,
    KreditBee) were employee-SSO-walled, so they are recorded as
    walled-skip with no browser time spent on them
  - anything else -> needs-browser (batched exception list, not daily)

Usage:
  python3 tools/board_scout.py [--limit N] [--only SUBSTR] [--apply]
  --apply  append derived configs to browser_boards.json (default:
           report only, no config changes)
  Report: tools/board_scout_report.json (untracked scratch, not committed)
"""
import argparse
import html
import json
import os
import re
import sys
import time
import urllib.request

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS = os.path.join(SITE, "crawl_targets.json")
BOARDS = os.path.join(SITE, "browser_boards.json")
INSPECT = os.path.join(SITE, "inspect_progress.json")
REPORT = os.path.join(SITE, "tools", "board_scout_report.json")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
SKIP_OUTCOMES = {"already_covered", "failed"}


def norm_name(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = r.read(1_500_000)
            return r.geturl(), raw.decode("utf-8", "replace")
    except Exception:
        return None, None


def derive(company, final_url, page_html):
    """Return (verdict, entry-or-reason). Verdicts: derived, walled-skip,
    needs-browser, unreachable."""
    urls = []
    if final_url:
        urls.append(final_url)
    if page_html:
        urls += re.findall(r'href=["\']([^"\']+)["\']', page_html)
    urls += [html.unescape(u) for u in urls]
    blob = "\n".join(urls)

    m = re.search(r"https://([a-z0-9-]+\.darwinbox\.in)", blob)
    if m:
        return ("walled-skip",
                f"Darwinbox tenant {m.group(1)} — SSO-walled in 4/4 "
                "live checks, no probe spent")
    m = re.search(r"https://([a-z0-9-]+\.ripplehire\.com)", blob)
    if m:
        host = m.group(1)
        return ("derived", {"company": company,
                            "careers_url": f"https://{host}/candidate/careers",
                            "engine": "ripplehire",
                            "params": {"entry_url": f"https://{host}/candidate/careers",
                                       "api_url": f"https://{host}/candidate/candidatejobsearch",
                                       "source": "CAREERSITE",
                                       "max_pages": 100}})
    m = re.search(r"https://([a-z0-9.-]+\.oraclecloud\.com)/hcmUI/"
                  r"CandidateExperience/en/sites/(CX_[0-9]+)", blob)
    if m:
        return ("derived", {"company": company,
                            "careers_url": final_url or "",
                            "engine": "oracle",
                            "params": {"host": m.group(1), "site": m.group(2)}})
    m = re.search(r"https://([a-z0-9-]+\.peoplestrong\.com)", blob)
    if m:
        host = m.group(1)
        return ("derived", {"company": company,
                            "careers_url": f"https://{host}/job/joblist",
                            "engine": "peoplestrong",
                            "params": {"host": host,
                                       "entry_url": f"https://{host}/job/joblist",
                                       "max_pages": 100}})
    m = re.search(r"https://([a-z0-9-]+\.wd\d\.myworkdayjobs\.com)/"
                  r"([A-Za-z0-9_]+)", blob)
    if m:
        host, site = m.group(1), m.group(2)
        if site.lower() not in ("en-us", "en-gb"):
            tenant = host.split(".")[0]
            return ("derived", {"company": company,
                                "careers_url": final_url or "",
                                "engine": "workday",
                                "params": {"host": host, "tenant": tenant,
                                           "site": site}})
    for eng, pat in [
            ("greenhouse", r"boards\.greenhouse\.io/([A-Za-z0-9_-]+)"),
            ("lever", r"jobs\.lever\.co/([A-Za-z0-9_-]+)"),
            ("ashby", r"jobs\.ashbyhq\.com/([A-Za-z0-9_-]+)"),
            ("workable", r"https://([A-Za-z0-9_-]+)\.workable\.com"),
            ("recruitee", r"https://([A-Za-z0-9_-]+)\.recruitee\.com")]:
        m = re.search(pat, blob)
        if m:
            return ("derived", {"company": company,
                                "careers_url": final_url or "",
                                "engine": eng,
                                "params": {"slug": m.group(1)}})
    return ("needs-browser",
            "no proven platform pattern in page URL/links")


def engine_identity(entry):
    p = entry.get("params", {})
    return (entry["engine"],
            p.get("host") or p.get("slug") or p.get("entry_url") or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    targets = json.load(open(TARGETS))
    if isinstance(targets, dict):
        targets = targets.get("targets", [])
    cfg = json.load(open(BOARDS))
    wired_names = {norm_name(b["company"]) for b in cfg["boards"]}
    wired_ids = {engine_identity(b) for b in cfg["boards"]}
    inspected = {}
    if os.path.exists(INSPECT):
        try:
            inspected = json.load(open(INSPECT))
        except Exception:
            inspected = {}
    if not isinstance(inspected, dict):
        inspected = {}

    # Adopt already-proven wired_ready entries from the old inspection log.
    adopted = []
    for name, rec in inspected.items():
        if isinstance(rec, dict) and rec.get("outcome") == "wired_ready":
            entry = rec.get("entry")
            if entry and norm_name(entry.get("company", name)) not in wired_names \
                    and engine_identity(entry) not in wired_ids:
                adopted.append(entry)
                wired_names.add(norm_name(entry.get("company", name)))
                wired_ids.add(engine_identity(entry))

    todo = []
    for t in targets:
        name = t.get("company") or t.get("name") or ""
        if not name or norm_name(name) in wired_names:
            continue
        rec = inspected.get(name)
        if isinstance(rec, dict) and rec.get("outcome") in SKIP_OUTCOMES:
            continue
        if args.only and args.only.lower() not in name.lower():
            continue
        todo.append(t)
    if args.limit:
        todo = todo[:args.limit]

    derived, walled, need_browser, unreachable = [], [], [], []
    for t in todo:
        name = t.get("company") or t.get("name")
        url = t.get("careers_url") or t.get("search_url") or ""
        if not url:
            unreachable.append((name, "no careers URL in sheet"))
            continue
        final_url, page_html = fetch(url)
        if final_url is None:
            unreachable.append((name, "fetch failed/timeout"))
            continue
        verdict, payload = derive(name, final_url, page_html)
        if verdict == "derived":
            if engine_identity(payload) in wired_ids:
                continue  # same platform endpoint already wired
            derived.append(payload)
            wired_ids.add(engine_identity(payload))
        elif verdict == "walled-skip":
            walled.append((name, payload))
        else:
            need_browser.append((name, payload))
        time.sleep(0.2)

    added = []
    if args.apply:
        for entry in adopted + derived:
            cfg["boards"].append(entry)
            added.append(entry["company"])
        with open(BOARDS, "w") as f:
            json.dump(cfg, f, indent=1, ensure_ascii=False)

    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M"),
        "scanned": len(todo),
        "adopted_wired_ready": [e["company"] for e in adopted],
        "derived": [d["company"] for d in derived],
        "derived_detail": derived,
        "applied": added,
        "walled_skip": walled,
        "needs_browser": need_browser,
        "unreachable": unreachable,
    }
    with open(REPORT, "w") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    print(f"scanned: {len(todo)} | derived: {len(derived)} "
          f"(adopted wired_ready: {len(adopted)}) | "
          f"walled-skip: {len(walled)} | needs-browser: {len(need_browser)} "
          f"| unreachable: {len(unreachable)}")
    if args.apply:
        print(f"applied to {BOARDS}: {len(added)} boards")
    else:
        print("report only — no config changes (re-run with --apply)")
    print(f"report: {REPORT}")


if __name__ == "__main__":
    main()
