#!/usr/bin/env python3
"""Fetch remote jobs from RemoteOK's keyless public API.

Endpoint: https://remoteok.com/api (JSON list; the first element is a
legal notice, not a job — skipped by requiring a 'position' field).
Kept jobs: track-matched (title + tags + description via
fetch_ats.TRACK_FILTERS) under their track; unmatched jobs only when
they are plausibly apply-able from India (location mentions India, or
is Remote/Worldwide/Anywhere) — those land as General and the strict
retag pass re-checks them. Pure non-India, non-remote listings are
skipped. Merges into jobs.json, deduped by normalized (title, company).
"""
import json, os, re, sys, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_ats import TRACK_FILTERS, TRACK_LABELS, INDIA_RE, norm, _word_in

SITE = os.path.dirname(os.path.abspath(__file__))
JOBS_PATH = os.path.join(SITE, "jobs.json")

REMOTE_LOCS = {"remote", "worldwide", "anywhere", "remote - worldwide",
               "remote worldwide", "remote / worldwide"}


def main():
    req = urllib.request.Request(
        "https://remoteok.com/api",
        headers={"User-Agent": "Mozilla/5.0 (NaukriSala Jobs Board)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        feed = json.load(r)
    data = json.load(open(JOBS_PATH))
    jobs = data["jobs"]
    seen = {(norm(j.get("title")), norm(j.get("company"))) for j in jobs}

    added, per_track = 0, {}
    for j in feed:
        if not isinstance(j, dict) or not j.get("position"):
            continue
        title = (j.get("position") or "").strip()
        company = (j.get("company") or "").strip()
        url = j.get("apply_url") or j.get("url") or ""
        if not title or not company or not url:
            continue
        loc = (j.get("location") or "Remote").strip()
        tags = " ".join(j.get("tags") or [])
        desc = re.sub(r"<[^>]+>", " ", j.get("description") or "")[:2000]
        hay = norm(title + " " + tags + " " + desc)
        matched = [s for s, kws in TRACK_FILTERS.items()
                   if any(_word_in(hay, k) for k in kws)]
        if not matched:
            if INDIA_RE.search(loc) or norm(loc) in REMOTE_LOCS:
                matched = ["general"]
            else:
                continue
        key = (norm(title), norm(company))
        if key in seen:
            continue
        slug = matched[0]
        seen.add(key)
        jobs.append({
            "id": "rok_" + str(j.get("id") or abs(hash(key)))[-10:],
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
            "source": "remoteok",
            "publisher": "RemoteOK",
            "posted": (j.get("date") or "")[:10],
        })
        per_track[slug] = per_track.get(slug, 0) + 1
        added += 1
    data["fetched_at"] = time.strftime("%Y-%m-%d")
    data["total"] = len(jobs)
    with open(JOBS_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    print("RemoteOK merge by track:", per_track)
    print(f"Merged {added} RemoteOK jobs. Board total: {len(jobs)}.")


if __name__ == "__main__":
    main()
