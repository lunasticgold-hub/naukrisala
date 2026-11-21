#!/usr/bin/env python3
"""Verify every row of the OpenSEO audit sheet against the CURRENT site files.

The sheet (1AXo8XYefVhgyxdio2C2VQaxBv6UFrUGZfIRj9GLLwPk) is an OpenSEO audit
export. The audit crawled only 50 of 123 pages and may predate the 17-19 Nov
fixes, so each row is re-checked against the repo (which mirrors live) and
given a verdict: CONFIRMED (still wrong — needs a fix) or STALE (already
right — the audit row predates the fix).

Checks per row type:
- Duplicate meta description: compare the page's meta description with the
  other pages in its group.
- Missing H1: count <h1> on the page.
- Heading levels skip: extract h1-h6 in document order; a skip is a heading
  more than one level deeper than the previous heading (H1->H3, H2->H4).
- Meta description too long: length > 160.
- Title too long: <title> length > 60 (the audit's threshold; counts the
  full title tag including " | NaukriSala").

Usage: python3 audit_seo_sheet.py   (run from the repo root)
Reads the sheet live via hatch_gws_cli; also writes hidden_files/
seo-sheet-verification.json with the per-row verdicts.
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHEET = "1AXo8XYefVhgyxdio2C2VQaxBv6UFrUGZfIRj9GLLwPk"
CLI = "/opt/hatch/bin/hatch_gws_cli"
OUT = os.path.join(ROOT, "..", "goals", "placement-academy-launch",
                   "hidden_files", "seo-sheet-verification.json")


def fetch_sheet():
    out = subprocess.run(
        [CLI, "sheets", "spreadsheets", "values", "get", "--params",
         json.dumps({"spreadsheetId": SHEET, "range": "Sheet1!A1:Z100"})],
        capture_output=True, text=True, timeout=60, check=True)
    return json.loads(out.stdout).get("values", [])


def url_to_file(url):
    path = url.replace("https://naukrisala.in", "").lstrip("/")
    if path == "":
        return "index.html"
    return path


def page_facts(path):
    """title, meta description, h1 list, heading sequence for a repo file."""
    full = os.path.join(ROOT, path)
    if not os.path.exists(full):
        return None
    s = open(full, encoding="utf-8").read()
    # Strip script/style: headings inside JS template literals are not in the
    # static DOM a crawler parses (JS-rendered headings are a separate check).
    s = re.sub(r"<script[\s\S]*?</script>", "", s)
    s = re.sub(r"<style[\s\S]*?</style>", "", s)
    title = re.search(r"<title>(.*?)</title>", s, re.S)
    meta = re.search(
        r'<meta name="description" content="([^"]*)"', s)
    h1s = re.findall(r"<h1[^>]*>(.*?)</h1>", s, re.S)
    heads = [(int(m.group(1)), re.sub(r"<[^>]+>", "", m.group(2)).strip())
             for m in re.finditer(r"<h([1-6])[^>]*>(.*?)</h\1>", s, re.S)]
    return {
        "title": (title.group(1).strip() if title else ""),
        "meta": (meta.group(1) if meta else ""),
        "h1s": [re.sub(r"<[^>]+>", "", h).strip() for h in h1s],
        "heads": heads,
    }


def find_skips(heads):
    """Return list of (index, level, prev_level, heading_text) for skips."""
    skips = []
    prev = 0
    for i, (level, text) in enumerate(heads):
        if prev and level > prev + 1:
            skips.append((i, level, prev, text[:60]))
        prev = level
    return skips


def main():
    rows = fetch_sheet()
    assert rows and rows[0][0] == "Severity", rows[:1]
    verdicts = []
    for r in rows[1:]:
        sev, issue, url, details, _fix = (r + ["", "", "", "", ""])[:5]
        f = url_to_file(url)
        facts = page_facts(f)
        v = {"row": issue, "url": url, "file": f, "severity": sev}
        if facts is None:
            v.update(verdict="MISSING-FILE", note=f"no such file in repo: {f}")
            verdicts.append(v)
            continue
        if issue == "Duplicate meta description":
            det = json.loads(details) if details else {}
            others = det.get("otherUrls", [])
            group = [url] + others
            metas = {}
            for u in group:
                ff = page_facts(url_to_file(u))
                metas[u] = ff["meta"] if ff else None
            dup = len({m for m in metas.values() if m}) < len(
                [m for m in metas.values() if m])
            v.update(verdict="CONFIRMED" if dup else "STALE",
                     meta=facts["meta"], meta_len=len(facts["meta"]),
                     group_metas=metas)
        elif issue == "Missing H1 heading":
            v.update(verdict="CONFIRMED" if not facts["h1s"] else "STALE",
                     h1s=facts["h1s"])
        elif issue == "Heading levels skip":
            skips = find_skips(facts["heads"])
            v.update(verdict="CONFIRMED" if skips else "STALE",
                     skips=skips,
                     heads=[f"H{l}:{t[:40]}" for l, t in facts["heads"]])
        elif issue == "Meta description too long":
            v.update(verdict="CONFIRMED" if len(facts["meta"]) > 160 else "STALE",
                     meta=facts["meta"], meta_len=len(facts["meta"]))
        elif issue == "Title too long":
            v.update(verdict="CONFIRMED" if len(facts["title"]) > 60 else "STALE",
                     title=facts["title"], title_len=len(facts["title"]))
        elif issue == "Crawl stopped early: page limit":
            v.update(verdict="AUDIT-COVERAGE",
                     note="audit crawled 50/123 pages; not a page defect")
        else:
            v.update(verdict="UNKNOWN-ISSUE")
        verdicts.append(v)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(verdicts, open(OUT, "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)

    from collections import Counter
    counts = Counter((v["row"], v["verdict"]) for v in verdicts)
    print("== verdicts by issue ==")
    for (issue, verdict), n in sorted(counts.items()):
        print(f"  {verdict:12s} {issue:28s} {n}")
    print(f"\n{len(verdicts)} rows checked; {sum(1 for v in verdicts if v['verdict']=='CONFIRMED')} CONFIRMED, "
          f"{sum(1 for v in verdicts if v['verdict']=='STALE')} STALE")
    print(f"detail: {OUT}")
    print("\n== CONFIRMED rows (need a fix) ==")
    for v in verdicts:
        if v["verdict"] != "CONFIRMED":
            continue
        extra = ""
        if "meta_len" in v:
            extra = f" meta_len={v['meta_len']}"
        if "title_len" in v:
            extra = f" title_len={v['title_len']}"
        if "skips" in v:
            extra = " skips=" + "; ".join(
                f"H{lv} after H{pv} '{t}'" for _, lv, pv, t in v["skips"])
        print(f"  {v['row']:28s} {v['url']}{extra}")


if __name__ == "__main__":
    main()
