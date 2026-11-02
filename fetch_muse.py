#!/usr/bin/env python3
"""Fetch jobs from The Muse's keyless public API.

Endpoint: https://www.themuse.com/api/public/jobs (20 results/page).
The location=India parameter does NOT filter to India (it returns
mostly Flexible/Remote US listings), so relevance is enforced locally:
a job is kept only when its locations include India or Remote/Flexible
— track-matched under its track, otherwise as General (the strict
retag pass re-checks both). Pure on-site non-India listings are
skipped. Capped at 3 pages/run to bound volume. Merges into jobs.json,
deduped by normalized (title, company).
"""
import json, os, re, sys, time, urllib.request, urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_ats import TRACK_FILTERS, TRACK_LABELS, INDIA_RE, norm, _word_in

SITE = os.path.dirname(os.path.abspath(__file__))
JOBS_PATH = os.path.join(SITE, "jobs.json")
PAGES = 3


def get_page(page):
    url = ("https://www.themuse.com/api/public/jobs?"
           + urllib.parse.urlencode({"page": page, "location": "India"}))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main():
    data = json.load(open(JOBS_PATH))
    jobs = data["jobs"]
    seen = {(norm(j.get("title")), norm(j.get("company"))) for j in jobs}

    added, per_track = 0, {}
    for page in range(1, PAGES + 1):
        try:
            d = get_page(page)
        except Exception as e:  # noqa: BLE001
            print(f"[skip] muse page {page}: {e}", file=sys.stderr)
            continue
        for j in d.get("results", []):
            title = (j.get("name") or "").strip()
            company = ((j.get("company") or {}).get("name") or "").strip()
            url = ((j.get("refs") or {}).get("landing_page") or "").strip()
            if not title or not company or not url:
                continue
            loc = "; ".join(l.get("name", "") for l in j.get("locations", []))
            relevant = bool(INDIA_RE.search(loc) or
                            re.search(r"remote|flexible", loc, re.I))
            if not relevant:
                continue
            desc = re.sub(r"<[^>]+>", " ", j.get("contents") or "")[:2000]
            hay = norm(title + " " + desc)
            matched = [s for s, kws in TRACK_FILTERS.items()
                       if any(_word_in(hay, k) for k in kws)]
            slug = matched[0] if matched else "general"
            key = (norm(title), norm(company))
            if key in seen:
                continue
            seen.add(key)
            tail = url.rstrip("/").split("-")[-1] or str(abs(hash(key)))
            jobs.append({
                "id": "muse_" + re.sub(r"\W", "", tail)[-10:],
                "course": slug,
                "course_label": TRACK_LABELS.get(slug, "General"),
                "title": title,
                "company": company,
                "location": loc,
                "created": None,
                "contract": "",
                "snippet": desc[:280],
                "url": url,
                "direct_url": url,
                "resolved": True,
                "source": "muse",
                "publisher": "The Muse",
                "posted": (j.get("publication_date") or "")[:10],
            })
            per_track[slug] = per_track.get(slug, 0) + 1
            added += 1
        time.sleep(0.5)
    data["fetched_at"] = time.strftime("%Y-%m-%d")
    data["total"] = len(jobs)
    with open(JOBS_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    print("Muse merge by track:", per_track)
    print(f"Merged {added} Muse jobs. Board total: {len(jobs)}.")


if __name__ == "__main__":
    main()
