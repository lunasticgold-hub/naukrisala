#!/usr/bin/env python3
"""Browser-boards engine: pull jobs from employer career pages that have no
simple public feed — custom portals, JS-rendered (SPA) career sites, and
ATS platforms not covered by the other fetchers.

How it works (honest architecture):
  - Every career page loads its jobs from SOME JSON endpoint the page itself
    calls. This engine talks to that same endpoint directly (same data, no
    browser needed, runs fine inside the daily cron).
  - Boards are configured in browser_boards.json. Each board names an
    `engine` — one of the proven ATS engines below, or `generic_json` for a
    custom portal whose endpoint was found by discover_board.py.
  - True browser rendering cannot run in this sandbox (verified 2026-10-21:
    the sandbox browser cannot reach the internet), so there is deliberately
    NO headless-Chrome path here. Sites with no discoverable JSON endpoint
    are handled by a one-off live-browser inspection (find the XHR endpoint,
    then add it as generic_json) or, as a last resort, a scheduled
    browser-task extraction — never by guessing a URL.

Hard rules (per user 2026-10-24):
  - Course is always aml-kyc; every candidate passes aml_gate() (title-led
    v2) — no gate pass, no merge.
  - Location: India OR Remote/global (loc_ok from fetch_aml_boards).
  - Public pages only. Never log in, never scrape behind auth.
  - Merges into jobs.json, deduped by normalized (title, company).

Usage:
  python3 fetch_browser_boards.py [--dry-run] [--board NAME]
  BROWSER_BOARDS_JSON=/tmp/test.json python3 fetch_browser_boards.py --dry-run
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_ats import TRACK_LABELS, aml_gate, norm
from fetch_ats import board_jobs as ats_board_jobs
from fetch_ats2 import board_jobs as ats2_board_jobs
from fetch_aml_boards import loc_ok, workday_aml_jobs
from fetch_enterprise import eightfold_jobs, oracle_jobs, sr_jobs

SITE = os.path.dirname(os.path.abspath(__file__))
JOBS_PATH = os.path.join(SITE, "jobs.json")
DEFAULT_BOARDS = os.path.join(SITE, "browser_boards.json")
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


def dig(obj, path):
    """Dot-path into nested JSON (e.g. 'data.jobs' or 'items.0.list')."""
    cur = obj
    for part in path.split("."):
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
        if cur is None:
            return None
    return cur


def clean_html(text):
    return re.sub(r"<[^>]+>", " ", text or "")[:2000]


def generic_json_jobs(board):
    """Config-driven extraction from a custom portal's JSON endpoint.

    Config keys: api_url (may contain {offset} / {page}), method GET|POST,
    payload (POST body, {offset}/{page} substituted), jobs_path (dot path
    to the list), fields {title, location, url, desc, posted} (dot paths
    relative to each job object; url may be a prefix + field via
    url_prefix + url_field), pagination {kind: offset|page|next_url,
    step, start, param, next_path, max_pages}, headers (extra).
    """
    cfg = board["params"]
    out = []
    headers = {**UA, **cfg.get("headers", {})}
    method = cfg.get("method", "GET").upper()
    pag = cfg.get("pagination", {"kind": "none"})
    kind = pag.get("kind", "none")
    offset, page = pag.get("start", 0), pag.get("start", 1)
    for _ in range(pag.get("max_pages", 20)):
        url = cfg["api_url"].replace("{offset}", str(offset)).replace(
            "{page}", str(page))
        try:
            if method == "POST":
                payload = json.loads(json.dumps(cfg.get("payload", {})).replace(
                    "{offset}", str(offset)).replace("{page}", str(page)))
                d = post_json(url, payload)
            else:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=60) as r:
                    d = json.load(r)
        except Exception as e:  # noqa: BLE001
            print(f"[generic] {board['company']}: {e}", file=sys.stderr)
            break
        items = dig(d, cfg["jobs_path"]) or []
        if not items:
            break
        fields = cfg["fields"]
        for j in items:
            if not isinstance(j, dict):
                continue
            url_val = dig(j, fields["url"]) if "url" in fields else None
            if not url_val and cfg.get("url_prefix") and cfg.get("url_field"):
                url_val = cfg["url_prefix"] + str(dig(j, cfg["url_field"]) or "")
            out.append({
                "title": dig(j, fields["title"]) or "",
                "location": dig(j, fields.get("location", "")) or "",
                "url": url_val or "",
                "desc": clean_html(str(dig(j, fields.get("desc", "")) or "")),
                "posted": dig(j, fields.get("posted", "")) or "",
            })
        if kind == "offset":
            offset += pag.get("step", 20)
            if len(items) < pag.get("step", 20):
                break
        elif kind == "page":
            page += 1
        elif kind == "next_url":
            nxt = dig(d, pag["next_path"])
            if not nxt:
                break
            cfg = {**cfg, "api_url": nxt}
            pag = {"kind": "next_url", "next_path": pag["next_path"],
                   "max_pages": pag.get("max_pages", 20)}
        else:
            break
    return out


def engine_jobs(board):
    """Dispatch one board config to its engine. Returns posting dicts."""
    eng = board["engine"]
    p = board.get("params", {})
    if eng in ("greenhouse", "lever", "ashby"):
        return ats_board_jobs({"ats": eng, "slug": p["slug"]})
    if eng in ("workable", "recruitee", "personio", "breezy", "teamtailor"):
        return ats2_board_jobs({"ats": eng, "slug": p["slug"]})
    if eng == "workday":
        return workday_aml_jobs(p["host"], p["tenant"], p["site"])
    if eng == "smartrecruiters":
        return sr_jobs(p["slug"])
    if eng == "eightfold":
        return eightfold_jobs(p["slug"])
    if eng == "oracle":
        return oracle_jobs(p["host"], p["site"])
    if eng == "generic_json":
        return generic_json_jobs(board)
    raise ValueError(f"unknown engine: {eng}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch + gate, report counts, do NOT write jobs.json")
    ap.add_argument("--board", help="run only this board (by company name)")
    args = ap.parse_args()

    boards_path = os.environ.get("BROWSER_BOARDS_JSON", DEFAULT_BOARDS)
    cfg = json.load(open(boards_path))
    boards = cfg.get("boards", [])
    if args.board:
        boards = [b for b in boards
                  if b["company"].lower() == args.board.lower()]
        if not boards:
            print(f"no board named {args.board!r}")
            return
    if not boards:
        print("browser-boards: no boards configured, nothing to do.")
        return

    data = json.load(open(JOBS_PATH))
    jobs = data["jobs"]
    seen = {(norm(j.get("title")), norm(j.get("company"))) for j in jobs}
    added_total = 0
    for b in boards:
        company = b["company"]
        try:
            postings = engine_jobs(b)
        except Exception as e:  # noqa: BLE001
            print(f"[skip] {company}: {e}", file=sys.stderr)
            continue
        kept = 0
        for p in postings:
            if not p.get("url") or not loc_ok(p.get("location")):
                continue
            if not aml_gate(p.get("title"), p.get("desc") or ""):
                continue
            key = (norm(p["title"]), norm(company))
            if key in seen:
                continue
            seen.add(key)
            uid = re.sub(r"\D", "", p["url"])[-10:] or str(abs(hash(key)))[-10:]
            jobs.append({
                "id": "brw_" + uid,
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
                "source": "browser-boards",
                "publisher": company + " careers",
                "posted": p.get("posted", ""),
            })
            kept += 1
        added_total += kept
        print(f"[ok] {company} ({b['engine']}): {kept} added "
              f"({len(postings)} postings)")
        time.sleep(0.4)
    if args.dry_run:
        print(f"DRY RUN — would add {added_total}; jobs.json untouched.")
        return
    data["fetched_at"] = time.strftime("%Y-%m-%d")
    data["total"] = len(jobs)
    with open(JOBS_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"Merged {added_total} browser-board jobs. "
          f"Board total: {len(jobs)}.")


if __name__ == "__main__":
    main()
