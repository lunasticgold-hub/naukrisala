#!/usr/bin/env python3
"""Inject JSON-LD structured data into every NaukriSala page.

What it adds (all values taken from each page's own title, meta description
and canonical — nothing invented):
- Organization + WebSite on every page (no sameAs: no verified social
  handles exist; no address/phone: none verified — the demo form's WhatsApp
  number is a placeholder and must never be published as contact info).
- WebPage on main pages, Article on blog posts (no datePublished: posts
  carry no publish date in their files, and the "10 Nov 2026" string in them
  is the Batch 9 date, not a publish date — inventing one would be wrong).

Idempotent: the block lives between NS-JSONLD-START/END markers and is
replaced on re-run. On domain day, re-run with the new base:
    python3 jsonld_gen.py https://www.naukrisala.com
which rewrites canonical-derived URLs (canonical tags themselves are flipped
separately — see the domain-day checklist).

Usage: python3 jsonld_gen.py [BASE]   (run from the repo root)
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else \
    "https://lunasticgold-hub.github.io/naukrisala"

ORG_DESC = ("NaukriSala is a placement-first training academy — 100% online. "
            "Start with ₹15,000. The rest is paid only after you're placed, "
            "in easy installments from your salary.")
LOGO = BASE + "/assets/brand/ns-logo-blue.png"

START = "<!-- NS-JSONLD-START -->"
END = "<!-- NS-JSONLD-END -->"

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
DESC_RE = re.compile(r'<meta name="description" content="(.*?)">', re.S)
CANON_RE = re.compile(r'<link rel="canonical" href="(.*?)">', re.S)


def page_url(rel):
    if rel == "index.html":
        return BASE + "/"
    if rel.startswith("blog/"):
        return BASE + "/" + rel
    return BASE + "/" + rel


def build_graph(rel, title, desc, canonical):
    headline = re.sub(r"\s*\|\s*NaukriSala\s*$", "", title).strip() or title
    org = {"@type": "Organization", "@id": BASE + "/#organization",
           "name": "NaukriSala", "url": BASE + "/", "description": ORG_DESC,
           "logo": LOGO}
    site = {"@type": "WebSite", "@id": BASE + "/#website",
            "url": BASE + "/", "name": "NaukriSala",
            "publisher": {"@id": BASE + "/#organization"}}
    if rel.startswith("blog/"):
        page = {"@type": "Article", "headline": headline, "description": desc,
                "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
                "author": {"@id": BASE + "/#organization"},
                "publisher": {"@id": BASE + "/#organization"}}
    else:
        page = {"@type": "WebPage", "@id": canonical + "#webpage",
                "url": canonical, "name": headline, "description": desc,
                "isPartOf": {"@id": BASE + "/#website"},
                "about": {"@id": BASE + "/#organization"}}
    return {"@context": "https://schema.org", "@graph": [org, site, page]}


def main():
    files = ["index.html"]
    files += sorted(f for f in os.listdir(ROOT)
                    if f.endswith(".html") and f != "index.html"
                    and os.path.isfile(os.path.join(ROOT, f)))
    files += sorted("blog/" + f for f in os.listdir(os.path.join(ROOT, "blog"))
                    if f.endswith(".html"))
    changed, skipped = 0, []
    for rel in files:
        path = os.path.join(ROOT, rel)
        html = open(path).read()
        if "</head>" not in html:
            skipped.append(rel)
            continue
        title = TITLE_RE.search(html)
        desc = DESC_RE.search(html)
        canon = CANON_RE.search(html)
        if not (title and desc):
            skipped.append(rel)
            continue
        url = canon.group(1) if canon else page_url(rel)
        graph = build_graph(rel, title.group(1).strip(),
                            desc.group(1), url)
        payload = json.dumps(graph, ensure_ascii=False, indent=2)
        payload = payload.replace("</", "<\\/")
        block = (f"{START}\n"
                 f'<script type="application/ld+json">\n{payload}\n</script>\n'
                 f"{END}")
        # strip any previous injection, then insert before </head>
        html = re.sub(re.escape(START) + r".*?" + re.escape(END),
                      "", html, flags=re.S)
        html = html.replace("</head>", block + "\n</head>", 1)
        open(path, "w").write(html)
        changed += 1
    print(f"injected: {changed} files; skipped (no </head> or no title/meta): {skipped}")
    assert not skipped, skipped


if __name__ == "__main__":
    main()
