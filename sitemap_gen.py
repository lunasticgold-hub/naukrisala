#!/usr/bin/env python3
"""Regenerate sitemap.xml from the files actually on disk.

Root cause of the 28 Oct 2026 bug: the old sitemap listed blog URLs with a
double extension (blog/<slug>.html.html) because the generator appended
".html" to slugs that already ended in ".html". All 100 blog URLs 404'd.
This generator never appends an extension: it lists real files only.

Usage: python3 sitemap_gen.py   (run from the repo root; writes sitemap.xml)
"""
import os
from xml.sax.saxutils import escape

BASE = "https://lunasticgold-hub.github.io/naukrisala"
ROOT = os.path.dirname(os.path.abspath(__file__))

urls = [BASE + "/"]
for name in sorted(os.listdir(ROOT)):
    if name.endswith(".html") and name != "index.html" and os.path.isfile(os.path.join(ROOT, name)):
        urls.append(f"{BASE}/{name}")
blog_dir = os.path.join(ROOT, "blog")
if os.path.isdir(blog_dir):
    for name in sorted(os.listdir(blog_dir)):
        if name.endswith(".html") and os.path.isfile(os.path.join(blog_dir, name)):
            urls.append(f"{BASE}/blog/{name}")

lines = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for u in urls:
    lines.append(f"  <url><loc>{escape(u)}</loc></url>")
lines.append("</urlset>")
with open(os.path.join(ROOT, "sitemap.xml"), "w") as f:
    f.write("\n".join(lines) + "\n")
print(f"sitemap.xml written: {len(urls)} URLs (root + blog, real files only)")
bad = [u for u in urls if u.endswith(".html.html")]
assert not bad, f"double-extension URLs slipped through: {bad[:3]}"
