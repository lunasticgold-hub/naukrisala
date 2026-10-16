#!/usr/bin/env python3
"""Normalize + sort jobs.json. Run after all fetchers in daily_refresh.sh.

- fetched: date the job was first pulled into the board (YYYY-MM-DD).
  Existing values are kept; new jobs are stamped with today's date.
- contract: normalized to Full-time / Part-time / Contract / Internship / ''.
- city: canonical city extracted from location ('' when not listed).
- jobs sorted newest-first by (fetched, created) so fresh pulls sit on top.
"""
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


def main():
    d = json.load(open(JP))
    jobs = d["jobs"]
    today = datetime.date.today().isoformat()
    for j in jobs:
        j["fetched"] = j.get("fetched") or today
        j["contract"] = norm_contract(j.get("contract"))
        j["city"] = city_of(j.get("location"))
    jobs.sort(key=lambda j: (j["fetched"], j.get("created") or ""), reverse=True)
    d["jobs"] = jobs
    d["total"] = len(jobs)
    d["fetched_at"] = today
    json.dump(d, open(JP, "w"), ensure_ascii=False)
    print(f"normalized {len(jobs)} jobs (sorted newest-first)")


if __name__ == "__main__":
    main()
