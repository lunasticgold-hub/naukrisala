#!/usr/bin/env python3
"""Apply pending NaukriSala admin edits to the live site repo.

Sources of work (Supabase project "naukrisala", service key):
  - ns_site_edits rows with status='pending': replace old_text with new_text
    in the named repo file. The replacement only happens when old_text matches
    EXACTLY ONCE in the file (entity-tolerant match: ' vs &rsquo;, & vs &amp;,
    etc.). 0 or 2+ matches -> row marked 'failed' with the reason, skipped.
    Each applied edit gets its own commit + push.
  - ns_blog_drafts rows with status='approved': append to posts.js, run
    tools/generate_blog.py, add the sitemap entry, commit + push, mark
    'published'.

Usage:
  python3 apply_site_edits.py [--root DIR] [--dry-run] [--no-push] [--limit N]
    --root     repo dir (default ~/workspace/naukrisala-site)
    --dry-run  report what would happen; change nothing
    --no-push  TEST MODE ONLY: commit locally but skip the push (rows are
               still marked applied — only use against a throwaway repo copy)
    --limit    max rows per run (default 20)

Safety: never `git add -A`; only the files an edit touched. If a push fails,
the local commit is rolled back (git reset --hard HEAD~1) and the row stays
pending. A lock file stops two runs (or a clash with the daily jobs refresh)
from stepping on each other.
"""
import argparse
import fcntl
import html
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

TRACKS = ["AML & KYC", "ServiceNow", "STOM", "Data Science & AI",
          "Full Stack Python", "Cloud & DevOps", "Testing", "Finance Operations",
          "Career Change", "Interviews & Resume", "Jobs & Placement"]
LOCK_PATH = "/tmp/ns-apply-site-edits.lock"
DEFAULT_ROOT = os.path.expanduser("~/workspace/naukrisala-site")

# Characters that may appear either literally or as an HTML entity in the file.
ENTITY_ALTS = [
    ("'", ["'", "\u2019", "&rsquo;", "&#8217;", "&apos;"]),
    ('"', ['"', "\u201c", "\u201d", "&ldquo;", "&rdquo;", "&quot;", "&#34;"]),
    ("&", ["&", "&amp;", "&#38;"]),
    ("\u2014", ["\u2014", "&mdash;", "&#8212;"]),
    ("\u2013", ["\u2013", "&ndash;", "&#8211;"]),
    ("\u00b7", ["\u00b7", "&middot;", "&#183;"]),
    ("\u2026", ["\u2026", "&hellip;", "&#8230;"]),
    ("\u00a0", ["\u00a0", "&nbsp;", "&#160;"]),
]


def anchor_regex(old_text):
    """Regex matching old_text in the file, tolerating entity spellings.

    old_text may already contain entity spellings (e.g. '&amp;' from a
    browser's innerHTML) while the file has the literal character, or vice
    versa — so decode first, then let each character match any spelling.
    """
    old_text = html.unescape(old_text)
    parts = []
    for ch in old_text:
        alts = None
        for key, variants in ENTITY_ALTS:
            if ch == key:
                alts = variants
                break
        if alts:
            parts.append("(" + "|".join(re.escape(v) for v in alts) + ")")
        else:
            parts.append(re.escape(ch))
    return re.compile("".join(parts))


def load_secrets():
    vals = {}
    with open(os.path.expanduser("~/.config/naukrisala/secrets.env")) as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip().strip('"').strip("'")
    return vals


class SB:
    def __init__(self, url, key):
        self.url = url.rstrip("/")
        self.key = key

    def _req(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            self.url + path, data=data, method=method,
            headers={"apikey": self.key, "Authorization": f"Bearer {self.key}",
                     "Content-Type": "application/json",
                     "Prefer": "return=minimal"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, resp.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()[:500]

    def get(self, path):
        status, body = self._req("GET", path)
        if status != 200:
            raise RuntimeError(f"Supabase GET {path} failed: {status} {body}")
        return json.loads(body or "[]")

    def patch(self, path, body):
        status, resp = self._req("PATCH", path, body)
        if status not in (200, 204):
            raise RuntimeError(f"Supabase PATCH {path} failed: {status} {resp}")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def run(cmd, cwd, check=True):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed: {r.stderr.strip()[:300]}")
    return r


def git_push_with_retry(root):
    """Push; on failure pull --rebase once and retry. Returns True on success."""
    r = run(["git", "push", "origin", "main"], cwd=root, check=False)
    if r.returncode == 0:
        return True
    run(["git", "pull", "--rebase", "origin", "main"], cwd=root, check=False)
    r = run(["git", "push", "origin", "main"], cwd=root, check=False)
    return r.returncode == 0


def plain_to_html(body):
    """Draft plain text -> post body HTML (same shape as existing posts)."""
    blocks = re.split(r"\n\s*\n", body.strip())
    out = []
    for b in blocks:
        lines = [l.strip() for l in b.strip().split("\n") if l.strip()]
        if not lines:
            continue
        if all(l.startswith("- ") for l in lines):
            items = "".join(f"<li>{html.escape(l[2:].strip())}</li>" for l in lines)
            out.append(f"<ul>{items}</ul>")
        elif len(lines) == 1 and len(lines[0]) < 60 and not lines[0].endswith((".", "!", "?", ":")):
            out.append(f"<h3>{html.escape(lines[0])}</h3>")
        else:
            out.append("<p>" + " ".join(html.escape(l) for l in lines) + "</p>")
    return "".join(out)


def apply_site_edit(sb, root, row, dry_run, no_push):
    page, label = row["page"], row["label"]
    path = os.path.join(root, page)
    if not os.path.isfile(path):
        return fail(sb, row, f"file not found: {page}", dry_run)
    with open(path, encoding="utf-8") as f:
        content = f.read()
    matches = list(anchor_regex(row["old_text"]).finditer(content))
    if len(matches) != 1:
        return fail(sb, row,
                    f"old text found {len(matches)} times in {page} (expected exactly 1)",
                    dry_run)
    m = matches[0]
    new_content = content[:m.start()] + row["new_text"] + content[m.end():]
    if dry_run:
        print(f"  DRY-RUN would apply: {page} — {label}")
        return True
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    run(["git", "add", page], cwd=root)
    run(["git", "commit", "-q", "-m", f"Admin edit: {page} — {label}"], cwd=root)
    if no_push:
        print(f"  NO-PUSH applied (not pushed): {page} — {label}")
    elif not git_push_with_retry(root):
        run(["git", "reset", "--hard", "-q", "HEAD~1"], cwd=root)
        print(f"  PUSH FAILED, rolled back, left pending: {page} — {label}")
        return False
    sb.patch(f"/rest/v1/ns_site_edits?id=eq.{row['id']}",
             {"status": "applied", "applied_at": now_iso()})
    print(f"  published: {page} — {label}")
    return True


def fail(sb, row, reason, dry_run):
    print(f"  FAILED: {row['page']} — {row['label']}: {reason}")
    if not dry_run:
        sb.patch(f"/rest/v1/ns_site_edits?id=eq.{row['id']}",
                 {"status": "failed", "error": reason})
    return True  # failed rows don't stop the run; only push failures do


def publish_draft(sb, root, draft, dry_run, no_push):
    slug, title = draft["slug"], draft["title"]
    track = (draft.get("track") or "").strip()
    if track not in TRACKS:
        return fail_draft(sb, draft,
                          f"track {track!r} is not one of the 11 blog tracks", dry_run)
    if not re.fullmatch(r"[a-z0-9-]+", slug or ""):
        return fail_draft(sb, draft, f"bad slug {slug!r}", dry_run)
    out = subprocess.run(
        ["node", "-e",
         "const fs=require('fs');let src=fs.readFileSync('posts.js','utf8')"
         ".replace('const NS_POSTS','NS_POSTS');eval(src);"
         "console.log(JSON.stringify(NS_POSTS.map(p=>p.slug)))"],
        cwd=root, capture_output=True, text=True)
    if out.returncode != 0:
        return fail_draft(sb, draft, f"could not read posts.js: {out.stderr[:200]}", dry_run)
    if slug in json.loads(out.stdout):
        return fail_draft(sb, draft, f"slug {slug!r} already exists", dry_run)
    body = (draft.get("body") or "").strip()
    excerpt = (draft.get("excerpt") or "").strip()
    if not body or not excerpt:
        return fail_draft(sb, draft, "draft needs both an excerpt and a body", dry_run)
    words = len(body.split())
    read = max(1, round(words / 200))
    entry = (
        "  {\n"
        f"    slug: {json.dumps(slug, ensure_ascii=False)},\n"
        f"    title: {json.dumps(title, ensure_ascii=False)},\n"
        f"    track: {json.dumps(track, ensure_ascii=False)},\n"
        f"    read: {read},\n"
        f"    excerpt: {json.dumps(excerpt, ensure_ascii=False)},\n"
        f"    body: {json.dumps(plain_to_html(body), ensure_ascii=False)}\n"
        "  }"
    )
    if dry_run:
        print(f"  DRY-RUN would publish draft: {slug} ({track}, ~{read} min)")
        return True
    posts_path = os.path.join(root, "posts.js")
    with open(posts_path, encoding="utf-8") as f:
        posts_src = f.read()
    tail = "\n];"
    idx = posts_src.rfind(tail)
    if idx == -1:
        return fail_draft(sb, draft, "posts.js does not end with the expected closing", dry_run)
    before = posts_src[:idx]
    # the last entry may already carry a trailing comma — never add a second
    sep = "" if before.rstrip().endswith(",") else ","
    posts_src = before + sep + "\n" + entry + tail + posts_src[idx + len(tail):]
    with open(posts_path, "w", encoding="utf-8") as f:
        f.write(posts_src)
    gen = subprocess.run(["python3", "tools/generate_blog.py"],
                         cwd=root, capture_output=True, text=True)
    if gen.returncode != 0:
        # roll back posts.js so the next run starts clean
        run(["git", "checkout", "--", "posts.js"], cwd=root)
        return fail_draft(sb, draft,
                          f"generate_blog.py failed: {(gen.stderr or gen.stdout)[:300]}",
                          dry_run)
    sitemap_path = os.path.join(root, "sitemap.xml")
    sm_entry = f"  <url><loc>https://naukrisala.in/blog/{slug}.html</loc></url>"
    with open(sitemap_path, encoding="utf-8") as f:
        sm = f.read()
    if sm_entry not in sm:
        sm = sm.replace("</urlset>", sm_entry + "\n</urlset>", 1)
        with open(sitemap_path, "w", encoding="utf-8") as f:
            f.write(sm)
    run(["git", "add", "posts.js", "blog.html", f"blog/{slug}.html", "sitemap.xml"], cwd=root)
    run(["git", "commit", "-q", "-m", f"Admin blog: publish {slug}"], cwd=root)
    if no_push:
        print(f"  NO-PUSH published (not pushed): {slug}")
    elif not git_push_with_retry(root):
        run(["git", "reset", "--hard", "-q", "HEAD~1"], cwd=root)
        print(f"  PUSH FAILED, rolled back, left approved: {slug}")
        return False
    sb.patch(f"/rest/v1/ns_blog_drafts?id=eq.{draft['id']}", {"status": "published"})
    print(f"  published blog post: {slug}")
    return True


def fail_draft(sb, draft, reason, dry_run):
    print(f"  FAILED draft {draft.get('slug')}: {reason}")
    if not dry_run:
        sb.patch(f"/rest/v1/ns_blog_drafts?id=eq.{draft['id']}",
                 {"status": "failed", "error": reason})
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    if not os.path.isdir(os.path.join(root, ".git")):
        print(f"not a git repo: {root}"); return 2

    lock = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("another apply run is active, exiting"); return 0

    secrets = load_secrets()
    sb = SB(secrets["SUPABASE_NS_URL"], secrets["SUPABASE_NS_SERVICE_KEY"])

    if not args.dry_run:
        r = run(["git", "status", "--porcelain"], cwd=root)
        if r.stdout.strip():
            print("working tree is dirty, refusing to run"); return 1
        r = run(["git", "pull", "--rebase", "origin", "main"], cwd=root, check=False)
        if r.returncode != 0:
            print("git pull --rebase failed, refusing to run"); return 1

    edits = sb.get(f"/rest/v1/ns_site_edits?status=eq.pending"
                   f"&order=created_at.asc&limit={args.limit}")
    print(f"{len(edits)} pending site edit(s)")
    for row in edits:
        ok = apply_site_edit(sb, root, row, args.dry_run, args.no_push)
        if not ok:
            print("stopping: push failure"); return 1

    drafts = sb.get("/rest/v1/ns_blog_drafts?status=eq.approved"
                    f"&order=created_at.asc&limit={args.limit}")
    print(f"{len(drafts)} approved draft(s)")
    for d in drafts:
        ok = publish_draft(sb, root, d, args.dry_run, args.no_push)
        if not ok:
            print("stopping: push failure"); return 1

    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
