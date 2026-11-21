"""Apply the redesigned "Keep exploring" section to the hand-written pages
(the ones generate_blog.py does not own).

Usage: python3 tools/apply_related.py   (run from the repo root)

What it does, per page in tools/related.py PAGE_RELATED:
- Replaces the old `<div class="related-links">...</div>` pill strip with the
  new <section class="related"> markup (same spot in the page, same indent).
- Removes the now-dead .related-links overrides in jobs.html's inline
  <style> and renames the selector in apply.html's print CSS to .related.
- Verifies every rendered href exists on disk, has no self-link and no
  duplicate; prints a per-page report and fails loudly if a page has no
  old block to replace (never inserts blindly — placement matters).

Idempotent: re-running replaces the new section with a freshly rendered
one (the matcher looks for <section class="related"> first, then falls
back to the old <div class="related-links">).
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from related import PAGE_RELATED, render_related

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NEW_RE = re.compile(r'<section class="related" aria-label="Related pages">.*?</section>', re.DOTALL)
OLD_RE = re.compile(r'<div class="related-links">.*?</div>', re.DOTALL)


INDENT = "      "  # 6 spaces, the file style. Fixed, never derived from
# the current line: deriving it re-added the existing indent on every run
# and the first line doubled each time (96 spaces by the third run).


def replace_section(text, new_html):
    """Swap the existing related block (new or old markup) for new_html.
    Returns (text, replaced?). The block is re-indented to INDENT; the
    first line keeps any markup already on its line (jobs.html keeps its
    <div class="wrap"> on the same line as the section)."""
    for rx in (NEW_RE, OLD_RE):
        m = rx.search(text)
        if not m:
            continue
        line_start = text.rfind("\n", 0, m.start()) + 1
        prefix = text[line_start:m.start()]
        lines = new_html.split("\n")
        if prefix.strip() == "":
            # Block starts its own line: normalize the indent to INDENT.
            body = "\n".join([INDENT + lines[0]]
                             + [(INDENT + ln) if ln else ln
                                for ln in lines[1:]])
            return text[:line_start] + body + text[m.end():], True
        # Mid-line (e.g. jobs.html's wrap div): keep the prefix, first
        # line unindented, the rest at INDENT.
        body = "\n".join([lines[0]]
                         + [(INDENT + ln) if ln else ln for ln in lines[1:]])
        return text[:m.start()] + body + text[m.end():], True
    return text, False


def main():
    failures = []
    for fname, groups in sorted(PAGE_RELATED.items()):
        path = os.path.join(ROOT, fname)
        if not os.path.exists(path):
            print(f"SKIP {fname}: file missing")
            failures.append(fname)
            continue
        s = open(path, encoding="utf-8").read()
        current = fname[:-5] if fname.endswith(".html") else fname
        new_html = render_related(groups, prefix="", current=current)
        if not new_html:
            print(f"SKIP {fname}: nothing renders (check the config)")
            failures.append(fname)
            continue
        s2, replaced = replace_section(s, new_html)
        if not replaced:
            print(f"FAIL {fname}: no related block found to replace")
            failures.append(fname)
            continue
        open(path, "w", encoding="utf-8").write(s2)
        n_links = new_html.count("<li><a href=")
        print(f"OK   {fname}: {n_links} links")

    # Dead CSS cleanups that belong to the old component.
    jobs = os.path.join(ROOT, "jobs.html")
    s = open(jobs, encoding="utf-8").read()
    dead = (".related-links{gap:6px}.related-links span{display:none}"
            ".related-links a{font-size:11px;padding:5px 10px;border-width:1px}")
    if dead in s:
        open(jobs, "w", encoding="utf-8").write(s.replace(dead, ""))
        print("OK   jobs.html: removed dead .related-links mobile override")
    else:
        print("note jobs.html: mobile override already gone")

    apply_p = os.path.join(ROOT, "apply.html")
    s = open(apply_p, encoding="utf-8").read()
    if ".related-links,.cf-cluster" in s:
        open(apply_p, "w", encoding="utf-8").write(
            s.replace(".related-links,.cf-cluster", ".related,.cf-cluster"))
        print("OK   apply.html: print CSS now hides .related")
    else:
        print("note apply.html: print selector already updated")

    # --- blog post .html twins -------------------------------------------
    # The live post pages are the .html twins (they also carry JSON-LD and
    # the current stylesheet versions — never overwrite them wholesale).
    # Take the freshly generated <section> from each extensionless file
    # (generate_blog.py must have run first) and splice it in place of the
    # two old pill strips. Everything else in the twin is untouched.
    import json as _json
    import subprocess as _sp
    out = _sp.run(["node", "-e",
                   "const fs=require('fs');let src=fs.readFileSync('posts.js','utf8')"
                   ".replace('const NS_POSTS','NS_POSTS');eval(src);"
                   "console.log(JSON.stringify(NS_POSTS))"],
                  capture_output=True, text=True, check=True, cwd=ROOT)
    posts = _json.loads(out.stdout)
    two_strips = re.compile(
        r'<div class="related-links">.*?</div>\s*<div class="related-links">.*?</div>',
        re.DOTALL)
    blog_fail = 0
    for post in posts:
        slug = post["slug"]
        gen = os.path.join(ROOT, "blog", slug)
        twin = gen + ".html"
        if not os.path.exists(gen) or not os.path.exists(twin):
            print(f"FAIL blog/{slug}: generated file or twin missing")
            blog_fail += 1
            continue
        section = NEW_RE.search(open(gen, encoding="utf-8").read())
        if not section:
            print(f"FAIL blog/{slug}: no <section> in generated file")
            blog_fail += 1
            continue
        t = open(twin, encoding="utf-8").read()
        m = two_strips.search(t)
        if not m:
            # Already converted (or no strips): only accept the new section.
            if NEW_RE.search(t):
                continue
            print(f"FAIL blog/{slug}: no two-strip block in twin")
            blog_fail += 1
            continue
        line_start = t.rfind("\n", 0, m.start()) + 1
        prefix = t[line_start:m.start()]
        sec_lines = section.group(0).split("\n")
        if prefix.strip() == "":
            body = "\n".join([INDENT + sec_lines[0]]
                             + [(INDENT + ln) if ln else ln
                                for ln in sec_lines[1:]])
            open(twin, "w", encoding="utf-8").write(
                t[:line_start] + body + t[m.end():])
        else:
            body = "\n".join([sec_lines[0]]
                             + [(INDENT + ln) if ln else ln
                                for ln in sec_lines[1:]])
            open(twin, "w", encoding="utf-8").write(
                t[:m.start()] + body + t[m.end():])
    print(f"blog twins: {len(posts) - blog_fail}/{len(posts)} updated"
          + (f", {blog_fail} failed" if blog_fail else ""))
    failures.extend(["blog"] * blog_fail)

    if failures:
        print(f"\n{len(failures)} page(s) need attention: {failures}")
        sys.exit(1)
    print("\ndone.")


if __name__ == "__main__":
    main()
