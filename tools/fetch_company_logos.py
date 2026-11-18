#!/usr/bin/env python3
"""
Fetch company logos for the NaukriSala jobs board.

Reads jobs.json, ranks companies by job count (most jobs first), and saves
a local logo for each company under assets/logos/.

Logo domain is derived from the company name with the SAME normalization
as jobs.html:
  - strip parentheticals, e.g. "Citigroup (Citi)" -> "Citigroup"
  - lowercase, remove every non-alphanumeric char -> logoKey
    e.g. "GitLab" -> "gitlab", "J.P. Morgan" -> "jpmorgan"
  - look the key up in LOGO_OVERRIDES, else append ".com"

Download sources, in order (logo.clearbit.com is NOT used: unreachable
from this runtime):
  1. Google favicon service  https://www.google.com/s2/favicons?domain=<domain>&sz=128
  2. DuckDuckGo icons        https://icons.duckduckgo.com/ip3/<domain>.ico
The first URL that returns HTTP 200 with a real image (content-type
image/*, size > 500 bytes, recognised image magic) is saved as
assets/logos/<logoKey>.png (or .jpg/.ico if that is what the service
actually returned).

A valid existing <logoKey> file (png/svg/ico/jpg) is reused instead of
re-downloading. Writes assets/logos/manifest.json mapping
logoKey -> filename, merged with any manifest already on disk so the
script is resumable.

Usage:
  python3 tools/fetch_company_logos.py [--limit N] [--workers N]
      [--extra-overrides path.json] [--force] [--jobs jobs.json]
"""
import argparse
import collections
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_JOBS = os.path.join(ROOT, "jobs.json")
DEFAULT_OUT = os.path.join(ROOT, "assets", "logos")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# Must stay in sync with LOGO_OVERRIDES in jobs.html.
LOGO_OVERRIDES = {
    "exl": "exlservice.com",
    "kpmgindia": "kpmg.com",
    "wnsglobalservices": "wns.com",
    "mufg": "mufg.jp",
    "drreddyslaboratories": "drreddys.com",
    "kotakmahindrabank": "kotak.com",
    "ernstyoung": "ey.com",
    "sarvam": "sarvam.ai",
    "cred": "cred.club",
    "groww": "groww.in",
    "tcs": "tcs.com",
    "tataconsultancyservices": "tcs.com",
    "hcltechnologies": "hcltech.com",
    "hcltech": "hcltech.com",
    "ltimindtree": "ltimindtree.com",
    "pricewaterhousecoopers": "pwc.com",
    "pwc": "pwc.com",
    "byjus": "byjus.com",
    "ola": "olacabs.com",
    "zeta": "zeta.tech",
    "meta": "meta.com",
    "facebook": "facebook.com",
}

IMAGE_EXTS = (".png", ".svg", ".ico", ".jpg", ".jpeg")
MIN_BYTES = 500        # preferred: a full-size favicon/logo
SMALL_MIN_BYTES = 150  # fallback: a genuine 16x16 favicon is 150-500 bytes;
                       # below that it is a 1x1 pixel / placeholder, not a logo


def logo_key(name):
    s = re.sub(r"\([^)]*\)", "", str(name or "")).lower()
    return re.sub(r"[^a-z0-9]", "", s)


def logo_domain(name, extra=None):
    k = logo_key(name)
    if not k:
        return "", k
    if extra and k in extra:
        return extra[k], k
    return LOGO_OVERRIDES.get(k, k + ".com"), k


def _magic_ok(path, min_bytes=MIN_BYTES):
    """True if the file looks like a real image (and > min_bytes)."""
    try:
        if os.path.getsize(path) <= min_bytes:
            return False
        with open(path, "rb") as f:
            head = f.read(16)
    except OSError:
        return False
    if head.startswith(b"\x89PNG"):
        return True
    if head.startswith(b"\xff\xd8\xff"):
        return True
    if head.startswith(b"GIF87a") or head.startswith(b"GIF89a"):
        return True
    if head.startswith(b"\x00\x00\x01\x00"):
        return True  # ICO
    if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        return True
    if head.startswith(b"BM"):
        return True
    # SVG is text: sniff the start of the file.
    try:
        with open(path, "rb") as f:
            txt = f.read(1024).lstrip().lower()
        if txt.startswith(b"<svg") or txt.startswith(b"<?xml"):
            return b"<svg" in txt
    except OSError:
        pass
    return False


def existing_logo(out_dir, key):
    """Return the filename of a valid existing <key> file, else None.

    Uses the small-file threshold: a genuine 16x16 favicon can be
    150-500 bytes and is still a real logo worth reusing.
    """
    for ext in IMAGE_EXTS:
        fn = key + ext
        p = os.path.join(out_dir, fn)
        if os.path.isfile(p) and _magic_ok(p, SMALL_MIN_BYTES):
            return fn
    return None


def curl_fetch(url, timeout=10):
    """Fetch url with curl. Returns (http_code, content_type, tmp_path or None).

    Retries once on a network-level failure (curl error / HTTP 000).
    """
    tmp = None
    for attempt in (1, 2):
        fd, tmp = tempfile.mkstemp(prefix="logo-", dir="/tmp")
        os.close(fd)
        cmd = [
            "curl", "-sS", "-L", "--max-time", str(timeout),
            "-A", UA, "-o", tmp, "-w", "%{http_code}|%{content_type}", url,
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        except subprocess.TimeoutExpired:
            r = None
        if r is not None and r.returncode == 0:
            out = (r.stdout or "").strip()
            code, _, ctype = out.partition("|")
            if code != "000":
                return code, ctype, tmp
        # Network failure: clean up and retry once.
        try:
            os.unlink(tmp)
        except OSError:
            pass
        tmp = None
        if attempt == 1:
            time.sleep(0.5)
    return "000", "", None


def ext_for(path, ctype):
    if ctype.startswith("image/png"):
        return ".png"
    if ctype.startswith("image/jpeg"):
        return ".jpg"
    if ctype in ("image/x-icon", "image/vnd.microsoft.icon"):
        return ".ico"
    if ctype.startswith("image/gif"):
        return ".gif"
    if ctype.startswith("image/webp"):
        return ".webp"
    if ctype.startswith("image/svg"):
        return ".svg"
    try:
        with open(path, "rb") as f:
            head = f.read(12)
        if head.startswith(b"\x89PNG"):
            return ".png"
        if head.startswith(b"\xff\xd8\xff"):
            return ".jpg"
        if head.startswith(b"\x00\x00\x01\x00"):
            return ".ico"
        if head.startswith(b"GIF8"):
            return ".gif"
    except OSError:
        pass
    return ".png"


def download_logo(domain, out_dir, key):
    """Try Google favicon, then DuckDuckGo, then the www. variant of each.

    Returns (filename, source, info). Preferred: a real image > 500 bytes.
    Fallback: if none has one, accept the largest genuine small favicon
    (> 150 bytes, e.g. a 16x16 mark) rather than leaving the company
    with no logo at all. The www. variant matters: some sites only have
    their favicon indexed under www.<domain> (e.g. statestreet.com,
    citco.com), while the bare domain 404s on both services.
    """
    attempts = [
        ("google", "https://www.google.com/s2/favicons?domain=%s&sz=128" % domain),
        ("ddg", "https://icons.duckduckgo.com/ip3/%s.ico" % domain),
    ]
    if not domain.startswith("www."):
        attempts += [
            ("google-www", "https://www.google.com/s2/favicons?domain=www.%s&sz=128" % domain),
            ("ddg-www", "https://icons.duckduckgo.com/ip3/www.%s.ico" % domain),
        ]
    errors = []
    small = None  # (size, source, ctype, tmp_path)
    for source, url in attempts:
        time.sleep(0.2)
        code, ctype, tmp = curl_fetch(url)
        if tmp is None:
            errors.append("%s:net-fail" % source)
            continue
        valid = (code == "200" and ctype.startswith("image/")
                 and _magic_ok(tmp, SMALL_MIN_BYTES))
        size = os.path.getsize(tmp) if os.path.isfile(tmp) else 0
        if valid and size > MIN_BYTES:
            ext = ext_for(tmp, ctype)
            fn = key + ext
            dest = os.path.join(out_dir, fn)
            shutil.move(tmp, dest)  # tmp is on /tmp (different fs) — move handles cross-device
            _cleanup_small(small)
            return fn, source, os.path.getsize(dest)
        if valid and size > SMALL_MIN_BYTES:
            if small is None or size > small[0]:
                _cleanup_small(small)
                small = (size, source, ctype, tmp)
            else:
                _cleanup_tmp(tmp)
        else:
            errors.append("%s:%s" % (source, code))
            _cleanup_tmp(tmp)
    if small is not None:
        size, source, ctype, tmp = small
        ext = ext_for(tmp, ctype)
        fn = key + ext
        dest = os.path.join(out_dir, fn)
        shutil.move(tmp, dest)
        return fn, source + "-small", size
    return None, None, ";".join(errors)


def _cleanup_tmp(tmp):
    if tmp:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _cleanup_small(small):
    if small is not None:
        _cleanup_tmp(small[3])


def process_one(args):
    key, company, count, domain, out_dir, force = args
    if not force:
        fn = existing_logo(out_dir, key)
        if fn:
            return {"key": key, "company": company, "count": count,
                    "domain": domain, "status": "reuse", "file": fn}
    fn, source, info = download_logo(domain, out_dir, key)
    if fn:
        return {"key": key, "company": company, "count": count,
                "domain": domain, "status": "download:" + source, "file": fn}
    return {"key": key, "company": company, "count": count,
            "domain": domain, "status": "fail", "file": None, "error": info}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jobs", default=DEFAULT_JOBS)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--limit", type=int, default=300,
                    help="process the top N companies by job count (0 = all)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--extra-overrides", default=None,
                    help="JSON file mapping logoKey -> domain, applied on top of LOGO_OVERRIDES")
    ap.add_argument("--force", action="store_true",
                    help="re-download even when a valid local file exists")
    args = ap.parse_args()

    extra = {}
    if args.extra_overrides:
        with open(args.extra_overrides) as f:
            extra = json.load(f)

    with open(args.jobs) as f:
        data = json.load(f)
    jobs = data["jobs"] if isinstance(data, dict) else data
    counts = collections.Counter(
        (j.get("company") or "").strip() for j in jobs if (j.get("company") or "").strip()
    )
    ranked = counts.most_common()
    if args.limit and args.limit > 0:
        ranked = ranked[: args.limit]

    # Dedupe by logoKey, keeping the highest-count company name.
    seen = {}
    for company, count in ranked:
        domain, key = logo_domain(company, extra)
        if not key or not domain:
            continue
        if key not in seen:
            seen[key] = (company, count, domain)
    todo = [(key, company, count, domain, args.out, args.force)
            for key, (company, count, domain) in seen.items()]
    print("companies total: %d | processing: %d (limit=%s)"
          % (len(counts), len(todo), args.limit), flush=True)

    os.makedirs(args.out, exist_ok=True)
    results = []
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(process_one, t): t for t in todo}
        for fut in concurrent.futures.as_completed(futs):
            r = fut.result()
            results.append(r)
            done += 1
            if r["status"] == "reuse":
                print("[%d/%d] REUSE  %-28s %-28s %s"
                      % (done, len(todo), r["key"], r["company"][:28], r["file"]), flush=True)
            elif r["status"].startswith("download"):
                print("[%d/%d] OK     %-28s %-28s %s (%s)"
                      % (done, len(todo), r["key"], r["company"][:28], r["file"], r["status"]), flush=True)
            else:
                print("[%d/%d] FAIL   %-28s %-28s %s [%s]"
                      % (done, len(todo), r["key"], r["company"][:28], r["domain"], r.get("error", "")), flush=True)

    # Merge with the manifest already on disk (keeps logos from earlier runs).
    manifest_path = os.path.join(args.out, "manifest.json")
    manifest = {}
    if os.path.isfile(manifest_path):
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
        except (OSError, ValueError):
            manifest = {}
    kept = {}
    for k, fn in manifest.items():
        p = os.path.join(args.out, fn)
        if os.path.isfile(p) and _magic_ok(p, SMALL_MIN_BYTES):
            kept[k] = fn
    for r in results:
        if r["file"]:
            kept[r["key"]] = r["file"]
    # Order the manifest by job count (desc), then key.
    order = {key: -i for i, (key, _, _, _, _, _) in enumerate(todo)}
    manifest = {k: kept[k] for k in sorted(kept, key=lambda k: (order.get(k, 0), k))}
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=False)
        f.write("\n")

    n_reuse = sum(1 for r in results if r["status"] == "reuse")
    n_dl = sum(1 for r in results if r["status"].startswith("download"))
    n_fail = sum(1 for r in results if r["status"] == "fail")
    print("\nSUMMARY: processed=%d reuse=%d downloaded=%d failed=%d manifest_entries=%d"
          % (len(results), n_reuse, n_dl, n_fail, len(manifest)))
    print("manifest: %s" % manifest_path)
    fails = sorted((r for r in results if r["status"] == "fail"),
                   key=lambda r: -r["count"])
    if fails:
        print("FAILED (top 30 by job count):")
        for r in fails[:30]:
            print("  %5d  %-32s key=%-28s domain=%s [%s]"
                  % (r["count"], r["company"][:32], r["key"], r["domain"], r.get("error", "")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
