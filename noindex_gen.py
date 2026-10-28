#!/usr/bin/env python3
"""Add <meta name="robots" content="noindex"> to every NaukriSala page EXCEPT
index.html (the home page), per the user's order of 28 Oct 2026: github.io is
temporary staging until launch, and nothing is to be done on index.

Why meta noindex (not robots.txt Disallow): robots.txt stays Allow-all so
crawlers can actually read the noindex directive and drop the URLs; a
Disallow would hide the directive itself and leave URL-only listings behind.

Reversible: the tag lives between NS-NOINDEX markers. At launch, run with
--remove to strip every tag, and re-run jsonld_gen.py / sitemap_gen.py with
the production BASE.

Usage: python3 noindex_gen.py [--remove]   (run from the repo root)
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
START = "<!-- NS-NOINDEX-START -->"
END = "<!-- NS-NOINDEX-END -->"
TAG = '<meta name="robots" content="noindex">'
REMOVE = "--remove" in sys.argv


def main():
    files = sorted(f for f in os.listdir(ROOT)
                   if f.endswith(".html") and f != "index.html"
                   and os.path.isfile(os.path.join(ROOT, f)))
    files += sorted("blog/" + f for f in os.listdir(os.path.join(ROOT, "blog"))
                    if f.endswith(".html"))
    changed = 0
    for rel in files:
        path = os.path.join(ROOT, rel)
        html = open(path).read()
        html = re.sub(re.escape(START) + r".*?" + re.escape(END),
                      "", html, flags=re.S)
        if not REMOVE:
            if "</head>" not in html:
                print(f"SKIP (no </head>): {rel}")
                continue
            html = html.replace("</head>",
                                f"{START}{TAG}{END}\n</head>", 1)
        open(path, "w").write(html)
        changed += 1
    # index.html is deliberately never touched by this script (it is not in
    # the file list above, so it cannot gain or lose the tag here).
    print(f"{'removed from' if REMOVE else 'added to'}: {changed} files "
          f"(index.html untouched)")


if __name__ == "__main__":
    main()
