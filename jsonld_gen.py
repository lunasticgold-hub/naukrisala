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
- Course on the 5 course pages (name/duration/fees parsed from the page
  itself; no duration when the page states none) and FAQPage on faq.html
  (all 15 Q&As parsed from the page — never hand-typed).

Idempotent: the block lives between NS-JSONLD-START/END markers and is
replaced on re-run. On domain day, re-run with the new base:
    python3 jsonld_gen.py https://naukrisala.in
which rewrites canonical-derived URLs (canonical tags themselves are flipped
separately — see the domain-day checklist).

Usage: python3 jsonld_gen.py [BASE]   (run from the repo root)
"""
import html as htmlmod
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else \
    "https://naukrisala.in"

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


COURSE_PAGES = {"course-aml-kyc.html", "course-servicenow.html",
                "course-data-science-ai.html", "course-stom.html",
                "course-full-stack-python.html"}

DUR_RE = re.compile(r"(\d+)\s*(day|days|month|months)")
FAQ_RE = re.compile(
    r'<div class="faq-item">\s*<button[^>]*>(.*?)<span class="plus">.*?</span>'
    r'</button>\s*<div class="faq-a">(.*?)</div>\s*</div>', re.S)


def _text(s):
    return htmlmod.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def _iso_duration(text):
    m = DUR_RE.search(text or "")
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2)
    return f"P{n}D" if unit.startswith("day") else f"P{n}M"


def build_course(rel, canonical, desc, html):
    """Course node from the page's own H1, meta line and fees line."""
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    if not h1:
        return None
    meta = re.search(r'<p class="course-hero-meta">(.*?)</p>', html, re.S)
    course = {"@type": "Course", "@id": canonical + "#course",
              "name": _text(h1.group(1)), "description": desc,
              "provider": {"@id": BASE + "/#organization"},
              "courseMode": "online"}
    dur = _iso_duration(meta.group(1) if meta else "")
    if dur:
        course["hasCourseInstance"] = {"@type": "CourseInstance",
                                       "courseMode": "online",
                                       "courseWorkload": dur}
    if "₹15,000 to start" in html:
        course["offers"] = {
            "@type": "Offer", "price": "15000", "priceCurrency": "INR",
            "description": ("₹15,000 to start. The rest is paid only after "
                            "you're placed, in installments from your salary.")}
    return course


def build_faq(canonical, html):
    """FAQPage node from the page's own 15 Q&A items."""
    items = []
    for q, a in FAQ_RE.findall(html):
        q, a = _text(q), _text(a)
        if q and a:
            items.append({"@type": "Question", "name": q,
                          "acceptedAnswer": {"@type": "Answer", "text": a}})
    if not items:
        return None
    return {"@type": "FAQPage", "@id": canonical + "#faq",
            "mainEntity": items}


def build_graph(rel, title, desc, canonical, html=""):
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
    graph = [org, site, page]
    if rel in COURSE_PAGES:
        course = build_course(rel, canonical, desc, html)
        if course:
            graph.append(course)
    if rel == "faq.html":
        faq = build_faq(canonical, html)
        if faq:
            graph.append(faq)
    return {"@context": "https://schema.org", "@graph": graph}


def main():
    files = ["index.html"]
    files += sorted(f for f in os.listdir(ROOT)
                    if f.endswith(".html") and f != "index.html"
                    and f != "admin.html"  # app shell, not a content page
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
                            desc.group(1), url, html)
        payload = json.dumps(graph, ensure_ascii=False, indent=2)
        payload = payload.replace("</", "<\\/")
        block = (f"{START}\n"
                 f'<script type="application/ld+json">\n{payload}\n</script>\n'
                 f"{END}")
        # strip any previous injection, then insert before </head>
        html = re.sub(re.escape(START) + r".*?" + re.escape(END),
                      "", html, flags=re.S)
        # the strip leaves the blank lines that framed the old block;
        # collapse them so re-runs don't grow the head by 2 lines each time
        html = re.sub(r"\n{3,}", "\n\n", html)
        html = html.replace("</head>", block + "\n</head>", 1)
        open(path, "w").write(html)
        changed += 1
    print(f"injected: {changed} files; skipped (no </head> or no title/meta): {skipped}")
    assert not skipped, skipped


if __name__ == "__main__":
    main()
