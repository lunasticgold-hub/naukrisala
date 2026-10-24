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
  - EVERY job is classified into one of the 15 courses (TRACK_FILTERS) and
    only jobs matching a course merge — a posting matching NO course is
    dropped, never dumped into a generic bucket. This is the user's
    "scrape all jobs which align with other courses, classify each post"
    order, and it preserves the older "don't add a job if it's not
    relevant" rule: relevance = matches a real course.
  - aml-kyc classification additionally requires aml_gate() (title-led v2):
    a posting that merely mentions compliance/risk/fraud in passing is NOT
    an AML role; if it also matches another course it lands there instead.
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
from fetch_ats import AML_STRONG, TRACK_FILTERS, TRACK_LABELS, aml_gate, norm
from fetch_ats import board_jobs as ats_board_jobs
from fetch_ats2 import board_jobs as ats2_board_jobs
from fetch_aml_boards import loc_ok
from fetch_enterprise import eightfold_jobs, oracle_jobs, post_json, sr_jobs

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


def _track_keywords(slug):
    """Keywords used for classification. aml-kyc uses the gate's full
    vocabulary (TRACK_FILTERS misses industry terms like SAR, KYX,
    Actimize, fincrime that the gate already understands)."""
    if slug == "aml-kyc":
        return list(dict.fromkeys(TRACK_FILTERS["aml-kyc"] + AML_STRONG +
                                  ["sar", "cdd", "edd"]))
    return TRACK_FILTERS[slug]


def _kw_positions(text, kw):
    """All start positions of kw in text. 'java' never matches inside
    'javascript'; short tokens (sar, cdd, edd, qa) match whole words only,
    mirroring _word_in (so 'sar' never trips on 'salary')."""
    if kw == "java":
        return [m.start() for m in re.finditer(r"java(?!script)", text)]
    if len(kw) <= 3:
        pat = r"(?<![a-z])" + re.escape(kw) + r"(?![a-z])"
        return [m.start() for m in re.finditer(pat, text)]
    pos, out = 0, []
    while True:
        i = text.find(kw, pos)
        if i < 0:
            return out
        out.append(i)
        pos = i + len(kw)


def classify(title, desc):
    """Course slug for a posting, or None if it matches no course.

    Two passes, title first — this is what the old first-match-wins rule
    got wrong (a snippet mention could override the actual job title):
      1. TITLE pass: the track whose keyword appears earliest IN THE TITLE
         wins ("Java & Python Developer" -> java; "Manager - .Net, Python"
         -> dotnet). aml-kyc title matches additionally require aml_gate().
         "java" never matches inside "javascript".
      2. SNIPPET fallback: only when the title names no course at all
         (generic titles like "Associate" or "Consultant") — first matching
         track in TRACK_FILTERS order, aml-kyc still gated.
    A posting matching neither pass returns None (caller sends it to
    General); a snippet mention can never override a title match.
    """
    t = norm(title or "")
    best, best_pos = None, None
    for slug in TRACK_FILTERS:
        if slug == "aml-kyc" and not aml_gate(title, desc):
            continue
        for k in _track_keywords(slug):
            for pos in _kw_positions(t, k):
                if best_pos is None or pos < best_pos:
                    best, best_pos = slug, pos
    if best:
        return best
    hay = norm(str(title or "") + " " + (desc or ""))
    for slug in TRACK_FILTERS:
        if slug == "aml-kyc" and not aml_gate(title, desc):
            continue
        if any(_kw_positions(hay, k) for k in _track_keywords(slug)):
            return slug
    return None


def workday_all_jobs(host, tenant, site):
    """Workday CXS, ALL jobs (empty search), paginated — classification
    happens in main(), so this must not pre-filter to AML terms."""
    out, seen, offset = [], set(), 0
    for _ in range(200):
        try:
            d = post_json(f"https://{host}/wday/cxs/{tenant}/{site}/jobs",
                          {"appliedFacets": {}, "limit": 20,
                           "offset": offset, "searchText": ""})
        except Exception as e:  # noqa: BLE001
            print(f"[workday] {host}: {e}", file=sys.stderr)
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
            bullets = " ".join(str(b) for b in (p.get("bulletFields") or []))
            out.append({"title": p.get("title"),
                        "location": p.get("locationsText") or "",
                        "url": url, "desc": bullets})
        offset += 20
        if d.get("total") and offset >= d["total"]:
            break
        time.sleep(0.5)
    return out


def clean_html(text):
    return re.sub(r"<[^>]+>", " ", text or "")[:2000]


def generic_html_jobs(board):
    """Config-driven extraction from a server-rendered HTML jobs page
    (no JSON API — the jobs are baked into the HTML, e.g. EY's
    SuccessFactors search). Config keys: list_url (with {offset}),
    row_pattern (regex with named groups title, url, location),
    url_prefix, pagination {step, max_pages}. Stops when a page yields
    no job rows. No detail-page fetches — title/location/link only, so
    classification runs on titles (which is the strict rule anyway).
    """
    import html as htmlmod

    cfg = board["params"]
    pat = re.compile(cfg["row_pattern"], re.S)
    step = cfg.get("pagination", {}).get("step", 25)
    max_pages = cfg.get("pagination", {}).get("max_pages", 40)
    out = []
    for page in range(max_pages):
        offset = page * step
        url = cfg["list_url"].replace("{offset}", str(offset))
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                html = r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            print(f"[html] {board['company']}: {e}", file=sys.stderr)
            break
        found = 0
        for m in pat.finditer(html):
            href = (m.group("url") or "").replace("&amp;", "&").strip()
            if not href:
                continue
            if href.startswith("/"):
                href = cfg.get("url_prefix", "").rstrip("/") + href
            elif not href.startswith("http"):
                continue
            title = htmlmod.unescape(
                re.sub(r"<[^>]+>", " ", m.group("title") or "")).strip()
            loc = htmlmod.unescape(
                re.sub(r"<[^>]+>", " ", m.group("location") or "")).strip()
            if not title:
                continue
            out.append({"title": title, "location": loc, "url": href,
                        "desc": "", "posted": ""})
            found += 1
        if not found:
            break
        time.sleep(0.4)
    return out


def ripplehire_jobs(board):
    """RippleHire SPA API (proven: HDFC Bank, 465 jobs).

    Flow: GET the public careers entry URL and follow its redirect to
    the tokenized portal URL; take the site token from that URL and use
    it ONLY in-memory for this run (never logged, never stored — it is
    the site's own public CAREERSITE link parameter). Then POST
    candidatejobsearch pages; the response is XML (JobPageVO with
    totalJobCount + jobVoList/jobVoList items). Apply links point at the
    public careers entry page, not a tokenized detail URL, so links
    never rot if the site token ever changes; each job gets a unique
    ?job=<jobSeq> query anchor (the portal ignores it) because the
    board's dedup collapses same-URL jobs — a shared entry URL alone
    silently killed 6 of HDFC's first 7 jobs. Cards show the Job ID
    for instant lookup on the portal.
    """
    import xml.etree.ElementTree as ET

    p = board["params"]
    opener = urllib.request.build_opener()
    req = urllib.request.Request(p["entry_url"], headers=UA)
    with opener.open(req, timeout=60) as r:
        final_url = r.url
    m = re.search(r"[?&]token=([^&#]+)", final_url)
    token = m.group(1) if m else ""
    out, page, total = [], 0, None
    max_pages = p.get("max_pages")
    while True:
        params = {"page": page, "search": "*:*", "token": token,
                  "source": p.get("source", "CAREERSITE"), "pagesize": 10}
        data = urllib.parse.urlencode(
            {"careerSiteUrlParams": json.dumps(params),
             "lang": "en"}).encode()
        req = urllib.request.Request(
            p["api_url"], data=data,
            headers={**UA,
                     "Content-Type": "application/x-www-form-urlencoded"})
        try:
            with opener.open(req, timeout=60) as r:
                root = ET.fromstring(r.read())
        except Exception as e:  # noqa: BLE001
            print(f"[ripplehire] {board['company']}: {e}", file=sys.stderr)
            break
        if total is None:
            try:
                total = int(root.findtext("totalJobCount") or 0)
            except ValueError:
                total = 0
        items = root.findall("./jobVoList/jobVoList")
        if not items:
            break
        for j in items:
            title = (j.findtext("jobTitle") or "").strip()
            if not title:
                continue
            loc = (j.findtext("locations") or "").strip()
            exp = (j.findtext("jobReqExp") or "").strip()
            openings = (j.findtext("numOfOpening") or "").strip()
            code = (j.findtext("jobCode") or "").strip()
            seq = (j.findtext("jobSeq") or "").strip()
            desc = " · ".join(x for x in
                              [exp + " experience" if exp else "",
                               openings + " openings" if openings else "",
                               "Job ID " + code if code else ""] if x)
            url = p["entry_url"] + ("?job=" + seq if seq else "")
            out.append({"title": title, "location": loc,
                        "url": url, "desc": desc, "posted": ""})
        page += 1
        if total and page * 10 >= total:
            break
        if max_pages and page >= max_pages:
            break
        time.sleep(0.4)
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
        return workday_all_jobs(p["host"], p["tenant"], p["site"])
    if eng == "smartrecruiters":
        return sr_jobs(p["slug"])
    if eng == "eightfold":
        return eightfold_jobs(p["slug"])
    if eng == "oracle":
        return oracle_jobs(p["host"], p["site"])
    if eng == "generic_json":
        return generic_json_jobs(board)
    if eng == "generic_html":
        return generic_html_jobs(board)
    if eng == "ripplehire":
        return ripplehire_jobs(board)
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
            course = classify(p.get("title"), p.get("desc") or "")
            if not course:
                continue
            key = (norm(p["title"]), norm(company))
            if key in seen:
                continue
            seen.add(key)
            uid = re.sub(r"\D", "", p["url"])[-10:] or str(abs(hash(key)))[-10:]
            jobs.append({
                "id": "brw_" + uid,
                "course": course,
                "course_label": TRACK_LABELS[course],
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
