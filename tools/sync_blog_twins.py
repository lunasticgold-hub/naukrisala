#!/usr/bin/env python3
"""Sync the live .html blog twins with posts.js after a title/body change.

The generator (tools/generate_blog.py) writes EXTENSIONLESS post files, but
the live pages are the .html twins, which carry their own JSON-LD and current
CSS versions and must never be overwritten from the extensionless byproducts.
So this script applies the same surgical replacements to each twin:
  - <title>, og:title, twitter:title: old title -> new title (88 renamed)
  - <h1>: old title -> new title
  - the post body's single <h3> -> <h2> (all 100 posts)
  - footer h4s were already fixed by tools/fix_seo_sheet.py; assert none left

Old titles come from git HEAD's posts.js; new titles and body h2 text from
the working tree's posts.js. Run after generate_blog.py, before
apply_related.py (which refreshes the Related section labels) and
jsonld_gen.py (which refreshes Article headlines from <title>).

Usage: python3 tools/sync_blog_twins.py   (from the repo root)
"""
import json
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_posts(source):
    """slug -> (title, body) from a posts.js text."""
    code = source.replace("const NS_POSTS", "NS_POSTS")
    out = subprocess.run(
        ["node", "-e",
         "let src=require('fs').readFileSync(0,'utf8');"
         "eval(src);"
         "console.log(JSON.stringify(NS_POSTS.map(p=>({slug:p.slug,title:p.title,body:p.body}))))"],
        input=code, capture_output=True, text=True, check=True)
    return {p["slug"]: (p["title"], p["body"]) for p in json.loads(out.stdout)}


def main():
    old = load_posts(subprocess.run(
        ["git", "show", "HEAD:posts.js"], cwd=ROOT,
        capture_output=True, text=True, check=True).stdout)
    new = load_posts(open(os.path.join(ROOT, "posts.js"), encoding="utf-8").read())
    assert set(old) == set(new), "slug sets differ between HEAD and worktree"
    renamed = {s for s in old if old[s][0] != new[s][0]}
    print(f"{len(old)} posts; {len(renamed)} renamed")

    fixed = 0
    for slug in sorted(old):
        twin = os.path.join(ROOT, "blog", slug + ".html")
        s = open(twin, encoding="utf-8").read()
        old_title, new_title = old[slug][0], new[slug][0]
        # body h2 text (new posts.js) -> the twin's h3 with the same text
        m = re.search(r"<h2>([^<]+)</h2>", new[slug][1])
        assert m, f"no body h2 in {slug}"
        body_h = m.group(1)
        subs = []
        if slug in renamed:
            pat = f"<title>{old_title} | NaukriSala</title>"
            assert s.count(pat) == 1, (slug, pat[:60], s.count(pat))
            subs.append((pat, pat.replace(old_title, new_title)))
            # og:title + twitter:title share this content string (2x)
            pat = f'content="{old_title} | NaukriSala"'
            assert s.count(pat) == 2, (slug, pat[:60], s.count(pat))
            subs.append((pat, pat.replace(old_title, new_title)))
            old_h1 = f"<h1>{old_title}</h1>"
            assert s.count(old_h1) == 1, (slug, "h1")
            subs.append((old_h1, f"<h1>{new_title}</h1>"))
        old_body = f"<h3>{body_h}</h3>"
        assert s.count(old_body) == 1, (slug, "body h3", s.count(old_body))
        subs.append((old_body, f"<h2>{body_h}</h2>"))
        assert "<h4>Top courses</h4>" not in s, f"footer h4 left in {slug}"
        for a, b in subs:
            s = s.replace(a, b)
        open(twin, "w", encoding="utf-8").write(s)
        fixed += 1
    print(f"twins synced: {fixed}/100")


if __name__ == "__main__":
    main()
