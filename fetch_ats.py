#!/usr/bin/env python3
"""Fetch India jobs per NaukriSala course from public ATS job-board APIs.

Sources: Greenhouse / Lever / Ashby public board APIs (keyless, unlimited).
Board list: ats_boards.json (verified slugs with India presence).
Apply links are the employer's own board URLs — zero intermediaries.
Merges into jobs.json, deduped by normalized (title, company).
"""
import json, os, re, sys, time, urllib.request, urllib.parse

SITE = os.path.dirname(os.path.abspath(__file__))
JOBS_PATH = os.path.join(SITE, "jobs.json")
BOARDS_PATH = os.path.join(SITE, "ats_boards.json")

INDIA_RE = re.compile(
    r"india|bengaluru|bangalore|mumbai|bombay|hyderabad|chennai|madras|"
    r"delhi|new delhi|gurgaon|gurugram|noida|pune|kolkata|calcutta|"
    r"ahmedabad|kochi|cochin|jaipur|lucknow|chandigarh|indore|surat|"
    r"nagpur|coimbatore|trivandrum|thiruvananthapuram|bhubaneswar|"
    r"mysore|mysuru|vijayawada|visakhapatnam|vizag|kanpur|patna|bhopal|"
    r"ludhiana|agra|nashik|faridabad|meerut|rajkot|varanasi|srinagar|"
    r"aurangabad|dhanbad|amritsar|allahabad|prayagraj|ranchi|howrah|"
    r"jabalpur|gwalior|thiruchirappalli|salem|tiruppur|vellore|"
    r"mangaluru|mangalore|gandhinagar|gift city|giftcity",
    re.I,
)

# slug -> filter keywords (client-side relevance; ATS APIs have no search)
TRACK_FILTERS = {
    "aml-kyc": ["aml", "kyc", "know your customer", "anti-money", "anti money",
                "compliance", "financial crime", "transaction monitoring",
                "due diligence", "sanctions", "fraud", "risk", "regulatory"],
    "servicenow": ["servicenow"],
    "data-science-ai": ["data scientist", "machine learning", "ml engineer",
                        "ai engineer", "deep learning", "llm", "genai"],
    "stom": ["service management", "itsm", "itil", "service transition",
             "service delivery"],
    "power-bi": ["power bi", "powerbi"],
    "data-analyst": ["data analyst", "data analytics"],
    "workday": ["workday"],
    "python-fullstack": ["python", "django", "flask", "fastapi"],
    "java-fullstack": ["java", "spring boot", "spring"],
    "qa-testing": ["qa", "quality assurance", "software test", "sdet",
                  "test engineer", "tester", "quality engineer"],
    "ib-operations": ["investment banking", "trade settlement",
                     "corporate actions", "reconciliation"],
    "sap-fico": ["sap fico", "s/4hana finance", "sap finance"],
    "web-dev": ["web developer", "frontend", "front-end", "react", "angular"],
    "dotnet": [".net", "dotnet", "c#", "asp.net"],
    "dbi": ["business intelligence", "bi developer", "etl", "data warehouse",
            "data engineer"],
}
TRACK_LABELS = {
    "aml-kyc": "AML & KYC Analyst", "servicenow": "ServiceNow Developer",
    "data-science-ai": "Data Science & AI Engineering",
    "stom": "STOM — Service Transition & Ops", "power-bi": "Power BI Developer",
    "data-analyst": "Data Analyst", "workday": "Workday Consultant",
    "python-fullstack": "Full Stack Python",
    "java-fullstack": "Full Stack Java Developer",
    "qa-testing": "Software Testing (QA)",
    "ib-operations": "Investment Banking Operations",
    "sap-fico": "SAP FICO (S/4HANA Finance)", "web-dev": "Web Development",
    "dotnet": ".NET Developer", "dbi": "Database & Business Intelligence",
}


def norm(s):
    return re.sub(r"\s+", " ", (s or "").lower().strip())


def get(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def board_jobs(board):
    ats, slug = board["ats"], board["slug"]
    if ats == "greenhouse":
        d = get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
        out = []
        for j in d.get("jobs", []):
            loc = (j.get("location") or {}).get("name", "")
            out.append({"title": j.get("title"), "location": loc,
                        "url": j.get("absolute_url"),
                        "desc": re.sub(r"<[^>]+>", " ",
                                       j.get("content") or "")[:2000]})
        return out
    if ats == "lever":
        d = get(f"https://api.lever.co/v0/postings/{slug}?mode=json")
        out = []
        for j in d if isinstance(d, list) else []:
            loc = (j.get("categories") or {}).get("location", "")
            out.append({"title": j.get("text"), "location": loc,
                        "url": j.get("hostedUrl"),
                        "desc": re.sub(r"<[^>]+>", " ",
                                       j.get("description") or "")[:2000]})
        return out
    if ats == "ashby":
        d = get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
                f"?includeCompensation=true")
        out = []
        for j in d.get("jobs", []):
            loc = (j.get("locationName") or j.get("location") or "")
            secs = j.get("secondaryLocations") or []
            if isinstance(secs, list):
                loc += " " + " ".join(str(s) for s in secs)
            out.append({"title": j.get("title"),
                        "location": loc,
                        "url": j.get("jobUrl"),
                        "desc": re.sub(r"<[^>]+>", " ",
                                       j.get("descriptionHtml") or "")[:2000]})
        return out
    return []


def is_india(loc):
    loc = loc or ""
    if not INDIA_RE.search(loc):
        return False
    return True


def main():
    boards = json.load(open(BOARDS_PATH))
    with open(JOBS_PATH) as f:
        data = json.load(f)
    jobs = data["jobs"]
    seen = {(norm(j.get("title")), norm(j.get("company"))) for j in jobs}

    added_total, per_track = 0, {s: 0 for s in TRACK_FILTERS}
    for b in boards:
        try:
            postings = board_jobs(b)
        except Exception as e:  # noqa: BLE001
            print(f"[skip] {b['company']}: {e}", file=sys.stderr)
            continue
        company = b["company"]
        for p in postings:
            if not p["url"] or not is_india(p["location"]):
                continue
            hay = norm(str(p["title"]) + " " + p["desc"])
            matched = [s for s, kws in TRACK_FILTERS.items()
                       if any(k in hay for k in kws)]
            for slug in matched:
                key = (norm(p["title"]), norm(company))
                if key in seen:
                    continue
                seen.add(key)
                jobs.append({
                    "id": "ats_" + slug[:3] + "_" + re.sub(r"\D", "", p["url"])[-10:],
                    "course": slug,
                    "course_label": TRACK_LABELS[slug],
                    "title": p["title"],
                    "company": company,
                    "location": p["location"],
                    "created": None,
                    "contract": "",
                    "snippet": p["desc"][:280],
                    "url": p["url"],
                    "direct_url": p["url"],
                    "resolved": True,
                    "source": "ats",
                    "publisher": company + " careers",
                    "posted": "",
                })
                per_track[slug] += 1
                added_total += 1
        time.sleep(0.4)
    data["fetched_at"] = time.strftime("%Y-%m-%d")
    data["total"] = len(jobs)
    with open(JOBS_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    print("ATS merge by track:", {k: v for k, v in per_track.items() if v})
    print(f"Merged {added_total} ATS jobs. Board total: {len(jobs)}.")


if __name__ == "__main__":
    main()


# ---------- AML/KYC relevance gate (strict; shared by AML-focused fetchers) ----------
def _word_in(text, token):
    # word-boundary match for short tokens (avoids "aml" matching "family");
    # substring match for longer phrases.
    if len(token) <= 3:
        return re.search(r"(?<![a-z])" + re.escape(token) + r"(?![a-z])",
                         text) is not None
    return token in text


def _has_any(text, tokens):
    return any(_word_in(text, t) for t in tokens)


AML_STRONG = [
    "aml", "kyc", "know your customer", "anti-money laundering",
    "anti money laundering", "anti-money-laundering", "money laundering",
    "transaction monitoring", "sanctions", "customer due diligence",
    "enhanced due diligence", "financial crime", "fincrime", "fin-crime",
    "suspicious activity", "suspicious transaction", "beneficial ownership",
    "politically exposed", "adverse media", "watchlist", "name screening",
    "trade-based money laundering", "correspondent banking",
    "regulatory compliance", "compliance monitoring",
]


def aml_gate(title, desc):
    """True only when the job is directly AML/KYC-related (v2, title-led).

    Why title-led: ATS descriptions carry company boilerplate ("we fight
    financial crime") that made every job at an AML company pass v1. So:
      - a strong anchor IN THE TITLE passes outright (even for engineering
        roles building AML systems, e.g. "AML Platform Engineer");
      - disqualifying function words (sales/engineering/marketing/design/
        IT/architect/talent-community) fail unless the title has an anchor;
      - adjacent titles (fraud/risk/compliance/screening/monitoring/...)
        pass only with AML/financial context in the description;
      - description-only anchors no longer pass (boilerplate).
    False negatives (generic-titled KYC ops roles) are accepted: the user's
    rule is "don't add a job if it's not relevant".
    """
    t, d = norm(title), norm(desc)
    if _has_any(t, AML_STRONG):
        return True
    if any(k in t for k in ["engineer", "developer", "designer", "architect",
                            "sales", "marketing", "campaign", "recruiter",
                            "talent acquisition", "human resources",
                            "account executive", "account manager",
                            "community", "data engineer",
                            "information technology", "customer success",
                            "business development"]):
        return False
    adjacent = ["fraud", "compliance", "investigat", "onboarding",
                "screening", "monitoring", "verification", "due diligence",
                "financial crime", "sanctions"]
    if any(k in t for k in adjacent) or _word_in(t, "risk"):
        if _has_any(d, ["aml", "kyc", "financial crime", "sanctions",
                        "compliance", "bank", "financial services",
                        "fintech", "payments"]):
            return True
    return False
