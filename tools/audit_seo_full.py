#!/usr/bin/env python3
"""Full-site SEO audit for naukrisala.in — the check the OpenSEO sheet's
50-page crawl could not do. Runs the sheet's own rules over EVERY page:

  - <title> present and <=60 chars
  - meta description present and <=160 chars, unique across the site
  - exactly one <h1>
  - no heading-level skips (a heading more than one level deeper than the
    previous heading; <script>/<style> stripped first, so JS template
    strings don't count)
  - canonical present

Scope: every tracked *.html page except admin.html (noindex, not in
sitemap) — root pages + blog/*.html. Reads the repo files (which mirror
live after push); use tools/audit_seo_sheet.py to re-check the sheet rows
themselves.

Usage: python3 tools/audit_seo_full.py   (from the repo root)
Exit code 0 when zero defects; prints every defect otherwise.
"""
import glob
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def page_facts(path):
    s = open(path, encoding="utf-8").read()
    s = re.sub(r"<script[\s\S]*?</script>", "", s)
    s = re.sub(r"<style[\s\S]*?</style>", "", s)
    title = re.search(r"<title>(.*?)</title>", s, re.S)
    meta = re.search(r'<meta name="description" content="([^"]*)"', s)
    canon = re.search(r'<link rel="canonical" href="([^"]*)"', s)
    h1s = re.findall(r"<h1[^>]*>(.*?)</h1>", s, re.S)
    heads = [(int(m.group(1)), re.sub(r"<[^>]+>", "", m.group(2)).strip())
             for m in re.finditer(r"<h([1-6])[^>]*>(.*?)</h\1>", s, re.S)]
    return {
        "title": title.group(1).strip() if title else "",
        "meta": meta.group(1) if meta else "",
        "canon": canon.group(1) if canon else "",
        "h1s": [re.sub(r"<[^>]+>", "", h).strip() for h in h1s],
        "heads": heads,
    }


def find_skips(heads):
    skips, prev = [], 0
    for level, text in heads:
        if prev and level > prev + 1:
            skips.append(f"H{level} after H{prev} '{text[:50]}'")
        prev = level
    return skips


def main():
    files = sorted(glob.glob(os.path.join(ROOT, "*.html")) +
                   glob.glob(os.path.join(ROOT, "blog", "*.html")))
    # admin.html is noindex; checkout.html is a noindex redirect stub.
    # noindex pages are deliberately unindexed, so SEO rules don't apply.
    files = [f for f in files
             if os.path.basename(f) not in ("admin.html", "checkout.html")]
    defects = []
    metas = defaultdict(list)
    for f in files:
        rel = os.path.relpath(f, ROOT)
        facts = page_facts(f)
        if not facts["title"]:
            defects.append(f"{rel}: MISSING title")
        elif len(facts["title"]) > 60:
            defects.append(f"{rel}: title {len(facts['title'])} chars: "
                           f"{facts['title']}")
        if not facts["meta"]:
            defects.append(f"{rel}: MISSING meta description")
        elif len(facts["meta"]) > 160:
            defects.append(f"{rel}: meta {len(facts['meta'])} chars")
        else:
            metas[facts["meta"]].append(rel)
        if len(facts["h1s"]) != 1:
            defects.append(f"{rel}: {len(facts['h1s'])} H1s: {facts['h1s']}")
        for sk in find_skips(facts["heads"]):
            defects.append(f"{rel}: heading skip {sk}")
        # 404.html is an error page, not indexable content; a canonical
        # on it is meaningless, so it is exempt from that one check.
        if not facts["canon"] and rel != "404.html":
            defects.append(f"{rel}: MISSING canonical")
    for meta, pages in metas.items():
        if len(pages) > 1:
            defects.append(f"DUPLICATE meta ({len(pages)}x): "
                           f"{meta[:60]}... on {', '.join(pages)}")

    print(f"pages checked: {len(files)}")
    if defects:
        print(f"DEFECTS: {len(defects)}")
        for d in defects:
            print(f"  - {d}")
        sys.exit(1)
    print("ZERO defects: all titles <=60, all metas <=160 and unique, "
          "exactly 1 H1 per page, no heading skips, canonicals present.")


if __name__ == "__main__":
    main()
