#!/usr/bin/env python3
"""Add a new blog post to NaukriSala.

Appends one post to posts.js (the source of truth), then regenerates the
blog (generate_blog.py), structured data (jsonld_gen.py) and the sitemap
(sitemap_gen.py).

Usage:
  python3 tools/add_blog_post.py --slug my-new-post --title "My new post" \
      --track "AML & KYC" --excerpt "One-line summary." \
      --body-file /path/to/body.html

  --body-file takes an HTML fragment for the post body (the <p>/<ul>/... HTML
  that goes inside <div class="post-body">). Or pass --body with the HTML
  inline, or --plain-text-file with plain text (blank line = new paragraph).

  --read sets the read time in minutes; if omitted it is estimated from the
  body text (~200 words/minute, minimum 1).

  --dry-run validates everything and prints the post that would be added,
  without writing anything. --root lets you test against a copy of the repo.

Rules enforced (the generator asserts these too):
  - slug must be unique and lowercase letters/numbers/hyphens only
  - track must be one of the 11 existing tracks (no new tracks)
  - title and excerpt must be non-empty

The script only writes local files. It does NOT commit or push — review the
new page (blog/<slug>.html) first, then commit and push as usual.
"""
import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load_posts(root):
    """Load NS_POSTS from posts.js via node, exactly like generate_blog.py."""
    code = (
        "const fs=require('fs');"
        "let src=fs.readFileSync('posts.js','utf8')"
        ".replace('const NS_POSTS','NS_POSTS');"
        "eval(src);console.log(JSON.stringify(NS_POSTS))"
    )
    out = subprocess.run(["node", "-e", code], cwd=root, capture_output=True,
                         text=True, check=True)
    return json.loads(out.stdout)


def load_tracks(root):
    """Read the TRACKS list from generate_blog.py so it cannot drift."""
    text = (root / "tools" / "generate_blog.py").read_text(encoding="utf-8")
    m = re.search(r"TRACKS = \[(.*?)\]", text, re.S)
    if not m:
        raise SystemExit("could not find TRACKS in tools/generate_blog.py")
    return json.loads("[" + m.group(1) + "]")


def body_from_plain_text(text):
    """Plain text -> HTML: blank line separates paragraphs."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    return "".join(f"<p>{html.escape(p)}</p>" for p in paras)


def build_js_object(post):
    """Render one post as a JS object literal (JSON strings are valid JS)."""
    fields = ["slug", "title", "track", "read", "excerpt", "body"]
    parts = []
    for f in fields:
        v = post[f]
        parts.append(f'    {f}: {json.dumps(v, ensure_ascii=False)}')
    return "{\n" + ",\n".join(parts) + "\n  }"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--track", required=True)
    ap.add_argument("--excerpt", required=True)
    ap.add_argument("--read", type=int, default=None)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--body-file", help="HTML fragment file for the body")
    group.add_argument("--body", help="HTML fragment, inline")
    group.add_argument("--plain-text-file",
                       help="plain-text file; blank line = new paragraph")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--root", default=str(REPO))
    args = ap.parse_args()
    root = Path(args.root)

    posts = load_posts(root)
    tracks = load_tracks(root)

    # --- validation ---
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.slug):
        raise SystemExit(f"bad slug {args.slug!r}: use lowercase letters, "
                         "numbers and hyphens only")
    if any(p["slug"] == args.slug for p in posts):
        raise SystemExit(f"slug {args.slug!r} already exists in posts.js")
    if args.track not in tracks:
        raise SystemExit(f"bad track {args.track!r}: must be one of "
                         f"{', '.join(tracks)}")
    if not args.title.strip() or not args.excerpt.strip():
        raise SystemExit("title and excerpt must be non-empty")

    if args.body_file:
        body = Path(args.body_file).read_text(encoding="utf-8").strip()
    elif args.body:
        body = args.body.strip()
    else:
        body = body_from_plain_text(
            Path(args.plain_text_file).read_text(encoding="utf-8"))
    if not body:
        raise SystemExit("post body is empty")

    read = args.read
    if read is None:
        words = len(re.sub(r"<[^>]+>", " ", body).split())
        read = max(1, round(words / 200))
    if read < 1:
        raise SystemExit("--read must be 1 or more")

    post = {"slug": args.slug, "title": args.title.strip(),
            "track": args.track, "read": read,
            "excerpt": args.excerpt.strip(), "body": body}

    print(f"post: {post['slug']} | {post['title']} | {post['track']} | "
          f"{post['read']} min read")
    if args.dry_run:
        print("--dry-run: nothing written")
        print(build_js_object(post))
        return 0

    # --- insert into posts.js, right before the closing ]; ---
    path = root / "posts.js"
    text = path.read_text(encoding="utf-8")
    marker = "\n];"
    idx = text.rfind(marker)
    if idx == -1:
        raise SystemExit("posts.js does not end with ]; — refusing to edit")
    text = text[:idx] + "\n  " + build_js_object(post) + ",\n];" + \
        text[idx + len(marker):]
    path.write_text(text, encoding="utf-8")
    print(f"added to posts.js ({len(posts) + 1} posts total)")

    # --- regenerate everything that derives from posts.js ---
    # NOTE: generate_blog.py writes extensionless files (blog/<slug>), but the
    # live pages are the .html twins (blog/<slug>.html) — those are the
    # tracked files GitHub Pages serves at the clean URL, the ones
    # jsonld_gen.py injects into, and the ones sitemap_gen.py lists. So the
    # new post's page must be copied to its .html twin before the other two
    # generators run. (Only the new post is copied: the other .html files
    # are maintained separately and must not be overwritten.)
    for script in ["tools/generate_blog.py"]:
        r = subprocess.run([sys.executable, script], cwd=root,
                           capture_output=True, text=True)
        print(f"{script}: exit {r.returncode} — "
              f"{(r.stdout or r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr).strip() else ''}")
        if r.returncode != 0:
            raise SystemExit(f"{script} failed:\n{r.stdout}\n{r.stderr}")

    import shutil
    page = root / "blog" / args.slug
    twin = root / "blog" / f"{args.slug}.html"
    if not page.exists():
        raise SystemExit(f"expected page blog/{args.slug} was not generated")
    shutil.copyfile(page, twin)
    print(f"copied blog/{args.slug} -> blog/{args.slug}.html (live page)")

    for script in ["jsonld_gen.py", "sitemap_gen.py"]:
        r = subprocess.run([sys.executable, script], cwd=root,
                           capture_output=True, text=True)
        print(f"{script}: exit {r.returncode} — "
              f"{(r.stdout or r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr).strip() else ''}")
        if r.returncode != 0:
            raise SystemExit(f"{script} failed:\n{r.stdout}\n{r.stderr}")

    page = root / "blog" / f"{args.slug}.html"
    if not page.exists():
        raise SystemExit(f"expected page blog/{args.slug}.html was not generated")
    sitemap = (root / "sitemap.xml").read_text(encoding="utf-8")
    if f"blog/{args.slug}" not in sitemap:
        raise SystemExit(f"blog/{args.slug} missing from sitemap.xml")
    print(f"OK: blog/{args.slug} generated and in sitemap.xml")
    print("Next: review the page, then commit + push (script does not push).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
