#!/usr/bin/env python3
"""Normalize + sort jobs.json. Run after all fetchers in daily_refresh.sh.

- fetched: date the job was first pulled into the board (YYYY-MM-DD).
  Existing values are kept; new jobs are stamped with today's date.
- contract: normalized to Full-time / Part-time / Contract / Internship / ''.
- city: canonical city extracted from location ('' when not listed).
- jobs sorted newest-first by (fetched, created) so fresh pulls sit on top.
"""
import html as htmlmod
import json
import os
import re
import datetime

SITE = os.path.dirname(os.path.abspath(__file__))
JP = os.path.join(SITE, "jobs.json")


def norm_contract(c):
    c = (c or "").strip().lower().replace("\u2013", "-").replace("_", "-").replace(" ", "-")
    if c in ("full-time", "fulltime"):
        return "Full-time"
    if c in ("part-time", "parttime"):
        return "Part-time"
    if c in ("contract", "contractor", "temporary", "temp"):
        return "Contract"
    if c in ("internship", "intern"):
        return "Internship"
    return ""


CITIES = [
    "Mumbai", "Delhi", "Bengaluru", "Bangalore", "Hyderabad", "Chennai", "Pune",
    "Kolkata", "Gurugram", "Gurgaon", "Noida", "Ahmedabad", "Jaipur", "Kochi",
    "Coimbatore", "Indore", "Nagpur", "Lucknow", "Chandigarh", "Bhopal",
    "Surat", "Vadodara", "Mysuru", "Mysore", "Thiruvananthapuram", "Trivandrum",
    "Visakhapatnam", "Bhubaneswar", "Guwahati", "Patna", "Ranchi", "Raipur",
    "Dehradun", "Amritsar", "Ludhiana", "Faridabad", "Ghaziabad", "Nashik",
    "Rajkot", "Vijayawada", "Madurai", "Kozhikode", "Ernakulam", "Mangaluru",
    "Mangalore", "Mysuru", "Kanpur", "Varanasi", "Agra", "Jodhpur", "Udaipur",
    "Panaji", "Puducherry", "Pondicherry", "Siliguri", "Cuttack", "Jamshedpur",
    "Dhanbad", "Ujjain", "Gwalior", "Jabalpur", "Ajmer", "Bikaner", "Mathura",
    "Bareilly", "Gorakhpur", "Haridwar", "Ambala", "Panipat", "Mohali",
]
ALIASES = {
    "Bangalore": "Bengaluru", "Gurgaon": "Gurugram", "Mysore": "Mysuru",
    "Mangalore": "Mangaluru", "Trivandrum": "Thiruvananthapuram",
    "Pondicherry": "Puducherry",
}


def city_of(loc):
    low = (loc or "").lower()
    for c in CITIES:
        if re.search(r"\b" + re.escape(c.lower()) + r"\b", low):
            return ALIASES.get(c, c)
    return ""


TRACK_PARAMS = re.compile(
    r"^(utm_[^=]*|utm|source|medium|campaign|term|content|ref|fbclid|gclid|mc_cid|mc_eid|igshid)$",
    re.I)


def canon_url(u):
    u = (u or "").strip()
    if not u:
        return ""
    u = u.split("#", 1)[0]
    if "?" in u:
        base, qs = u.split("?", 1)
        kept = sorted(
            p for p in qs.split("&")
            if p and not TRACK_PARAMS.match(p.split("=", 1)[0])
        )
        u = base + ("?" + "&".join(kept) if kept else "")
    return u.lower().rstrip("/")


def dedup_key(j):
    cu = canon_url(j.get("direct_url") or j.get("url"))
    if cu:
        return ("u", cu)
    t = re.sub(r"\s+", " ", (j.get("title") or "").lower().strip())
    c = re.sub(r"\s+", " ", (j.get("company") or "").lower().strip())
    l = (j.get("city") or "").lower() or re.sub(
        r"\s+", " ", (j.get("location") or "").lower().strip())
    return ("t", t, c, l)


def dedup(jobs):
    seen, out, dropped = set(), [], 0
    for j in jobs:  # jobs pre-sorted newest-first: first occurrence wins
        k = dedup_key(j)
        if k in seen:
            dropped += 1
            continue
        seen.add(k)
        out.append(j)
    return out, dropped


def clean_snippet(s):
    s = htmlmod.unescape(s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:280]


CUR_SYM = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£", "AED": "AED "}
PER_SFX = {"YEAR": "/yr", "MONTH": "/mo", "HOUR": "/hr", "WEEK": "/wk", "DAY": "/day"}


def salary_text(j):
    raw = (j.get("salary_text") or "").strip()
    if raw:
        return re.sub(r"\s+", " ", htmlmod.unescape(raw))[:80]
    mn, mx = j.get("salary_min"), j.get("salary_max")
    if mn is None and mx is None:
        return ""
    cur = (j.get("salary_currency") or "INR").upper()
    per = (j.get("salary_period") or "").upper()
    sfx = PER_SFX.get(per, "")

    def fmt(v):
        try:
            v = float(v)
        except (TypeError, ValueError):
            return ""
        if cur == "INR" and v >= 100000 and per in ("YEAR", ""):
            return f"₹{v / 100000:g} L"
        return f"{CUR_SYM.get(cur, cur + ' ')}{v:,.0f}"

    if mn and mx:
        try:
            if float(mn) == float(mx):
                return (fmt(mx) + sfx).strip()
        except (TypeError, ValueError):
            pass
        if cur == "INR" and per in ("YEAR", ""):
            try:
                a, b = float(mn) / 100000, float(mx) / 100000
                if a >= 1:
                    return f"₹{a:g}–{b:g} LPA"
            except (TypeError, ValueError):
                pass
        return f"{fmt(mn)}–{fmt(mx)}{sfx}".strip()
    return (fmt(mn or mx) + sfx).strip()


def main():
    d = json.load(open(JP))
    jobs = d["jobs"]
    today = datetime.date.today().isoformat()
    for j in jobs:
        j["fetched"] = j.get("fetched") or today
        j["contract"] = norm_contract(j.get("contract"))
        j["city"] = city_of(j.get("location"))
        j["snippet"] = clean_snippet(j.get("snippet"))
        j["salary_text"] = salary_text(j)
    jobs.sort(key=lambda j: (j["fetched"], j.get("created") or ""), reverse=True)
    jobs, dropped = dedup(jobs)
    d["jobs"] = jobs
    d["total"] = len(jobs)
    d["fetched_at"] = today
    json.dump(d, open(JP, "w"), ensure_ascii=False)
    print(f"normalized {len(jobs)} jobs (sorted newest-first, {dropped} duplicates removed)")


if __name__ == "__main__":
    main()
