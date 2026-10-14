#!/usr/bin/env python3
"""Extract the direct 'Apply for this job' link from each Adzuna job page.

Reads jobs.json, fetches each redirect_url (the Adzuna details page),
extracts the /land/ad/ apply href (which forwards straight to the employer),
and stores it as `direct_url`. Falls back to the original redirect_url.
No Adzuna API calls are used.
"""
import json, os, re, urllib.request
from concurrent.futures import ThreadPoolExecutor

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jobs.json")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
LAND_RE = re.compile(r'href="(https://www\.adzuna\.in/land/ad/[^"]+)"')
EASY_RE = re.compile(r'href="(https://www\.adzuna\.in/details/\d+/apply\?aztt=[^"]+)"')

def direct_for(url):
    try:
        req = urllib.request.Request(url, headers=UA)
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
        m = LAND_RE.search(html) or EASY_RE.search(html)
        if m:
            return m.group(1).replace("&amp;", "&")
    except Exception:  # noqa: BLE001
        pass
    return None

def main():
    with open(PATH) as f:
        data = json.load(f)
    jobs = data["jobs"]

    with ThreadPoolExecutor(max_workers=10) as ex:
        found = list(ex.map(direct_for, [j["url"] for j in jobs]))

    n = 0
    for j, d in zip(jobs, found):
        j["direct_url"] = d or j["url"]
        n += bool(d)

    with open(PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"Direct apply links: {n}/{len(jobs)}")

if __name__ == "__main__":
    main()
