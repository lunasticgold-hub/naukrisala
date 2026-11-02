#!/usr/bin/env python3
"""Fetch jobs DIRECTLY from employers' own career pages (no aggregators).

NaukriSala's internal career-pages engine. Two modes:
  - daily: reads career_pages.json, extracts jobs from each page, merges
    into jobs.json (deduped by normalized (title, company)).
  - one-off API: --url <careers page> --company <name> [--india-page]
    prints extracted jobs as JSON without touching jobs.json.

Extraction, in order, per page (zero per-site code):
  1. JSON-LD JobPosting blocks (schema.org) — most reliable.
  2. ATS-embed detection — if the page just embeds Greenhouse / Lever /
     Ashby / Workable / SmartRecruiters / Workday / Oracle, report the
     embed (it belongs in the existing ATS/enterprise registries)
     instead of scraping links.
  3. Listing-link heuristics — <a> tags pointing at job/career URLs
     with role-like text; nav/blog/culture links cut.
  4. AI fallback — only when GEMINI_KEY is present (secrets.env, never
     printed) and heuristics found <2 jobs, max 5 pages/run: the page
     text goes to a free-tier model that returns structured jobs.
     Without a key the engine reports the page as heuristic-empty.

Relevance: track-matched via fetch_ats.TRACK_FILTERS; unmatched India
jobs land as General on pages flagged "general": true (same rule as
the new ATS boards). India filter: pages flagged india_page accept all
extracted jobs; global pages accept only jobs whose title or URL
mentions India (INDIA_RE).
"""
import argparse
import html as htmlmod
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_ats import TRACK_FILTERS, TRACK_LABELS, INDIA_RE, norm, _word_in

SITE = os.path.dirname(os.path.abspath(__file__))
JOBS_PATH = os.path.join(SITE, "jobs.json")
REGISTRY_PATH = os.path.join(SITE, "career_pages.json")
AI_PAGES_PER_RUN = 5

# NOTE: matched against the URL *path* only, with a segment boundary —
# matching the full URL misfires on "https://careers.example.com/..."
# (the "//" of the scheme) and on "/careersatzoho" (social links).
JOB_HREF_RE = re.compile(
    r"/(job|jobs|career|careers|vacanc|opening|position|role|apply|"
    r"recruit|posting|opportunit)(/|$|-|_)", re.I)
JUNK_HREF_RE = re.compile(
    r"/(blog|news|about|contact|team|life|culture|benefit|investor|"
    r"press|event|login|sign|privacy|terms|cookie|sitemap)(/|$|-|_)", re.I)
JUNK_TITLE_EXACT = {
    "apply now", "view all", "see all jobs", "load more", "back to",
    "home", "careers home", "search jobs", "sign in", "log in",
    "register", "register here", "sign up", "follow us", "share",
    "subscribe", "filter", "all jobs", "all openings", "join us",
    "facebook", "instagram", "twitter", "linkedin", "youtube", "x",
    # nav phrases observed on real career pages (never job titles)
    "explore jobs", "openings", "english", "hindi", "chinese",
    "german", "हिंदी", "jobs at ntpc", "career growth & opportunities",
    "click here to view", "role & functions", "careers", "overview",
    "for graduates", "for experienced professionals", "archive",
    "archived openings", "why work with ongc", "recruitment policy",
    "results", "audio-visuals", "apprenticeship opportunities",
    "recruitment notices", "consultant", "inquiry officers",
}
JUNK_TITLE_SUB = (
    "talent pool", "talent community", "about us", "contact us",
    "our team", "life at", "working at", "press release",
    "investor relations", "privacy policy", "terms of",
)
ATS_EMBEDS = [
    ("greenhouse", re.compile(r"boards-api\.greenhouse\.io/v1/boards/([\w-]+)")),
    ("greenhouse", re.compile(r"boards\.greenhouse\.io/([\w-]+)")),
    ("lever", re.compile(r"jobs\.lever\.co/([\w-]+)")),
    ("lever", re.compile(r"api\.lever\.co/v0/postings/([\w-]+)")),
    ("ashby", re.compile(r"api\.ashbyhq\.com/posting-api/job-board/([\w-]+)")),
    ("workable", re.compile(r"apply\.workable\.com/api/v1/widget/accounts/([\w-]+)")),
    ("smartrecruiters", re.compile(r"api\.smartrecruiters\.com/v1/companies/([\w-]+)")),
    ("workday", re.compile(r"([\w-]+\.wd\d+\.myworkdayjobs\.com)")),
    ("oracle", re.compile(r"fa-[\w-]+\.fa\.ocs\.oraclecloud\.com")),
]


def get_html(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        charset = r.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")


def strip_tags(s):
    return re.sub(r"<[^>]+>", " ", s or "")


def clean_text(s):
    return re.sub(r"\s+", " ", htmlmod.unescape(strip_tags(s or ""))).strip()


def loc_to_str(loc):
    if not loc:
        return ""
    if isinstance(loc, str):
        return loc
    if isinstance(loc, list):
        return "; ".join(loc_to_str(x) for x in loc if loc_to_str(x))
    if isinstance(loc, dict):
        if loc.get("name"):
            return str(loc["name"])
        addr = loc.get("address") or {}
        if isinstance(addr, dict):
            parts = [addr.get("addressLocality", ""),
                     addr.get("addressRegion", ""),
                     addr.get("addressCountry", "")]
            return ", ".join(p for p in parts if p)
        return ""
    return ""


def json_ld_jobs(page_html, page_url):
    out = []
    for m in re.finditer(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            page_html, re.S | re.I):
        try:
            d = json.loads(m.group(1).strip())
        except Exception:  # noqa: BLE001 - malformed block, skip it
            continue
        items = []
        if isinstance(d, list):
            items = d
        elif isinstance(d, dict):
            if isinstance(d.get("@graph"), list):
                items = d["@graph"]
            else:
                items = [d]
        for j in items:
            if not isinstance(j, dict):
                continue
            t = j.get("@type")
            types = t if isinstance(t, list) else [t]
            if "JobPosting" not in types:
                continue
            title = clean_text(str(j.get("title") or j.get("name") or ""))
            if not title:
                continue
            org = j.get("hiringOrganization") or {}
            company = org.get("name") if isinstance(org, dict) else str(org)
            url = j.get("url") or page_url
            desc = clean_text(str(j.get("description") or ""))[:2000]
            posted = str(j.get("datePosted") or "")[:10]
            out.append({"title": title, "company": company or "",
                        "location": loc_to_str(j.get("jobLocation")),
                        "url": url, "desc": desc, "posted": posted})
    return out


def detect_embed(page_html):
    for ats, rx in ATS_EMBEDS:
        m = rx.search(page_html)
        if m:
            return {"ats": ats, "slug": m.group(1)}
    return None


def link_jobs(page_html, page_url):
    out, seen = [], set()
    for m in re.finditer(
            r'<a\s[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            page_html, re.S | re.I):
        href, inner = m.group(1).strip(), m.group(2)
        if not href or href.startswith(("#", "mailto:", "javascript:", "tel:")):
            continue
        url = urllib.parse.urljoin(page_url, href)
        path = urllib.parse.urlparse(url).path or ""
        if not JOB_HREF_RE.search(path) or JUNK_HREF_RE.search(path):
            continue
        title = clean_text(inner)
        # Strip trailing social/share button text baked into card links,
        # e.g. "... Noida India Facebook Twitter Linkedin Mail Add to
        # favorites Share" -> "... Noida India".
        title = re.sub(
            r"(\s+(facebook|twitter|linkedin|mail|add to favorites|share))+$",
            "", title, flags=re.I).strip()
        if not (4 <= len(title) <= 100):
            continue
        low = title.lower()
        if low in JUNK_TITLE_EXACT or low.startswith(
                ("view all", "see all", "load more", "back to", "search")):
            continue
        if any(s in low for s in JUNK_TITLE_SUB):
            continue
        key = (norm(title), url)
        if key in seen:
            continue
        seen.add(key)
        out.append({"title": title, "company": "", "location": "",
                    "url": url, "desc": "", "posted": ""})
    return out


def ai_extract(page_html, company, page_url, timeout=90):
    """LLM fallback: page text -> structured jobs. Needs GEMINI_KEY."""
    key = os.environ.get("GEMINI_KEY", "")
    if not key:
        return None
    text = clean_text(page_html)[:12000]
    if len(text) < 200:
        return []
    prompt = (
        "Extract every job posting visible in this career page text. "
        "Return ONLY a JSON array of objects with keys title, location, "
        "url (absolute URL if shown, else empty string). No other text.\n\n"
        + text)
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }).encode()
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           "gemini-3.8-flash:generateContent?key=" + key)
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.load(r)
        raw = d["candidates"][0]["content"]["parts"][0]["text"]
        arr = json.loads(raw)
    except Exception as e:  # noqa: BLE001
        print(f"[ai] {company}: extraction failed: {e}", file=sys.stderr)
        return []
    out = []
    for j in arr if isinstance(arr, list) else []:
        if not isinstance(j, dict) or not j.get("title"):
            continue
        out.append({"title": clean_text(str(j["title"])), "company": "",
                    "location": clean_text(str(j.get("location") or "")),
                    "url": j.get("url") or page_url, "desc": "",
                    "posted": ""})
    return out


def extract(board, ai_budget):
    """Returns (jobs, embed, ai_used). Jobs carry no company yet."""
    page_url = board["url"]
    page_html = get_html(page_url)
    embed = detect_embed(page_html)
    if embed:
        return [], embed, False
    jobs = json_ld_jobs(page_html, page_url)
    if len(jobs) < 2:
        jobs = jobs + [j for j in link_jobs(page_html, page_url)
                       if (norm(j["title"]), j["url"]) not in
                       {(norm(x["title"]), x["url"]) for x in jobs}]
    ai_used = False
    if len(jobs) < 2 and ai_budget[0] > 0:
        ai_budget[0] -= 1
        ai = ai_extract(page_html, board["company"], page_url)
        if ai:
            jobs = jobs + [j for j in ai
                           if (norm(j["title"]), j["url"]) not in
                           {(norm(x["title"]), x["url"]) for x in jobs}]
            ai_used = True
    return jobs, None, ai_used


def classify_jobs(board, raw_jobs):
    """Apply India filter + track matching. Returns job dicts to merge."""
    company = board["company"]
    india_page = bool(board.get("india_page"))
    out = []
    for p in raw_jobs:
        title = p["title"]
        if not india_page and not INDIA_RE.search(
                title + " " + (p.get("url") or "") + " " + p.get("location", "")):
            continue
        hay = norm(title + " " + p.get("desc", ""))
        matched = [s for s, kws in TRACK_FILTERS.items()
                   if any(_word_in(hay, k) for k in kws)]
        if not matched and board.get("general"):
            matched = ["general"]
        if not matched:
            continue
        slug = matched[0]
        out.append({
            "id": "cp_" + slug[:3] + "_" + (
                re.sub(r"\D", "", p["url"])[-10:]
                or str(abs(hash((norm(title), norm(company))))) [-10:]),
            "course": slug,
            "course_label": TRACK_LABELS.get(slug, "General"),
            "title": title,
            "company": company,
            "location": p.get("location", ""),
            "created": None,
            "contract": "",
            "snippet": p.get("desc", "")[:280],
            "url": p["url"],
            "direct_url": p["url"],
            "resolved": True,
            "source": "career-pages",
            "publisher": company + " careers",
            "posted": p.get("posted", ""),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="one-off: extract this career page")
    ap.add_argument("--company", default="")
    ap.add_argument("--india-page", action="store_true")
    ap.add_argument("--general", action="store_true", default=True)
    args = ap.parse_args()

    if args.url:
        board = {"company": args.company or "unknown",
                 "url": args.url, "india_page": args.india_page,
                 "general": args.general}
        try:
            raw, embed, ai_used = extract(board, [AI_PAGES_PER_RUN])
        except Exception as e:  # noqa: BLE001
            print(json.dumps({"error": str(e)}))
            return
        if embed:
            print(json.dumps({"embed": embed}))
            return
        print(json.dumps({"jobs": classify_jobs(board, raw),
                          "ai_used": ai_used}, indent=1, ensure_ascii=False))
        return

    boards = json.load(open(REGISTRY_PATH)) if os.path.exists(REGISTRY_PATH) else []
    if not boards:
        print("No career pages registered (career_pages.json empty).")
        return
    data = json.load(open(JOBS_PATH))
    jobs = data["jobs"]
    seen = {(norm(j.get("title")), norm(j.get("company"))) for j in jobs}
    ai_budget = [AI_PAGES_PER_RUN]
    added, per_track = 0, {}
    for b in boards:
        try:
            raw, embed, ai_used = extract(b, ai_budget)
        except Exception as e:  # noqa: BLE001
            print(f"[skip] {b['company']}: {e}", file=sys.stderr)
            continue
        if embed:
            print(f"[embed] {b['company']}: {embed['ats']} "
                  f"{embed['slug']} — add to ATS/enterprise registry")
            continue
        for job in classify_jobs(b, raw):
            key = (norm(job["title"]), norm(job["company"]))
            if key in seen:
                continue
            seen.add(key)
            jobs.append(job)
            per_track[job["course"]] = per_track.get(job["course"], 0) + 1
            added += 1
        print(f"[ok] {b['company']}: {len(raw)} extracted "
              f"({'ai' if ai_used else 'heuristics'})")
        time.sleep(0.5)
    data["fetched_at"] = time.strftime("%Y-%m-%d")
    data["total"] = len(jobs)
    with open(JOBS_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    print("Career-pages merge by track:", per_track)
    print(f"Merged {added} career-page jobs. Board total: {len(jobs)}.")


if __name__ == "__main__":
    main()
