#!/usr/bin/env python3
"""Fix every confirmed row of the OpenSEO audit sheet (plus the same defects
the partial 50-page crawl missed) on naukrisala.in.

Verified first with tools/audit_seo_sheet.py: 26 of the sheet's 92 rows were
already fixed by the 17-19 Nov Phase 2 work (unique metas, blog H1, 10
trimmed descriptions); 65 rows were confirmed live defects:
  - 38 heading-level skips (H1->H3 in post bodies and on 8 pages; H2->H4
    from the footer nav headings)
  - 27 titles over 60 chars
Plus the full-site scope the 50-page crawl missed: the same H1->H3 skip
exists in ALL 100 post bodies (not just the 30 crawled) and 88 of 100 post
titles exceed 60 chars with the brand suffix (not just the 24 crawled).

Fixes (visuals preserved — every retagged heading keeps its exact size via
a retargeted class-scoped CSS rule):
  A. CSS retargets (styles.css / home.css / jobs.html / apply.html inline).
  B. Footer nav headings h4 -> h2 site-wide (124 pages + generate_blog.py
     chrome, so future regens stay correct). H2 can never skip downward.
  C. posts.js: body <h3> -> <h2> (100x) + 88 titles shortened to <=47 chars
     (full <title> with " | NaukriSala" then <=60).
  D. Page headings: index demo h3->h2; ai-tools card h3s->h2, demo h4->h3,
     kw h5s->h4; apply v-head h3->h2, v-kw h4s->h3, ATS checklist h4->h3;
     courses + how-it-works persona h3s->h2; faq online-card h3->h2;
     jobs snapshot h3->h2 + fallback bc-job h4s->h3; privacy/terms h3s->h2
     with a .legal rule.
  E. Three page titles: fees, vs-career-cracker, placement-courses-bhubaneswar
     (title + og:title + twitter:title).

After this script: run tools/generate_blog.py, sync the .html twins
(tools/sync_blog_twins.py), tools/apply_related.py, jsonld_gen.py, then
tools/audit_seo_full.py to confirm zero remaining defects.

Usage: python3 tools/fix_seo_sheet.py   (from the repo root; dry-run with
--check to print what would change without writing)
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRY = "--check" in sys.argv

# slug -> new title (<=47 chars so "<title> | NaukriSala" is <=60)
TITLE_MAP = {
    "what-kyc-analysts-check-new-account": "What KYC analysts check in a new account",
    "sanctions-screening-false-positives-cleared": "Sanctions screening: clearing false positives",
    "transaction-monitoring-alerts-reading-scenario": "Reading a transaction monitoring alert",
    "sar-str-reports-useful-filing": "SAR and STR reports: filing one that helps",
    "adverse-media-checks-public-news": "Adverse media checks: risk in public news",
    "kyc-documents-spotting-mismatch": "KYC documents: spotting a mismatch early",
    "aml-interview-questions-judgement": "AML interview questions that test judgement",
    "servicenow-admin-vs-developer": "ServiceNow admin vs developer: which fits you",
    "incident-problem-change-itsm-tickets": "Incident, problem, change: how ITSM connects",
    "first-flow-designer-workflow-no-code": "Your first Flow Designer workflow, no code",
    "gliderecord-basics-new-developers": "GlideRecord basics for new developers",
    "servicenow-certifications-practical-order": "ServiceNow certifications: which order to take",
    "update-sets-work-missing-instances": "Update sets: why work goes missing",
    "servicenow-interview-scenarios": "ServiceNow interview scenarios that come up",
    "catalog-items-request-workflows": "Catalog items and request workflows, simply",
    "service-transition-vs-operations": "Service transition vs operations: the split",
    "change-enablement-checks-before-release": "Change enablement: checks before a release",
    "service-desk-to-operations-engineer": "Service desk to operations engineer: the path",
    "reading-an-sla-clearly": "Reading an SLA without getting lost",
    "shift-work-it-operations-nights": "Shift work in IT operations: staying sharp",
    "incident-bridges-down-systems": "Incident bridges: running the call when down",
    "monitoring-alerts-signal-vs-noise": "Monitoring alerts: signal vs noise",
    "itil-practices-real-operations-jobs": "ITIL practices in real operations jobs",
    "cleaning-messy-data-pandas": "Cleaning messy data with pandas",
    "train-test-split-false-confidence": "Train-test split: avoiding false confidence",
    "regression-vs-classification-model-type": "Regression vs classification: picking the type",
    "overfitting-ace-training-fail-live": "Overfitting: acing training, failing live",
    "prompting-llm-context-constraints-examples": "Prompting an LLM well: context and examples",
    "rag-grounding-answers-own-documents": "RAG in plain terms: grounding your answers",
    "data-portfolio-project-shows-thinking": "A data portfolio that shows your thinking",
    "sql-questions-data-interviews-practise": "SQL questions data interviews repeat",
    "evaluating-language-model-output": "Evaluating a language model output",
    "python-basics-carry-into-frameworks": "Python basics that carry into frameworks",
    "django-vs-flask-first-project": "Django vs Flask for your first project",
    "building-rest-api-frontend-use": "Building a REST API a frontend can use",
    "html-css-javascript-minimum-python-developer": "HTML, CSS, JS: the minimum a Python dev needs",
    "user-login-passwords-sessions-mistakes": "User login: passwords, sessions, mistakes",
    "deploying-small-python-app-setup": "Deploying a small Python app, simply",
    "debugging-python-reading-tracebacks": "Debugging Python: reading tracebacks",
    "full-stack-project-database-api-ui": "A full-stack project: database, API, UI",
    "aws-building-blocks-ec2-s3-iam": "AWS building blocks: EC2, S3, IAM",
    "cloud-support-roles-day-to-day": "Cloud support roles: the day-to-day work",
    "ci-cd-pipeline-commit-to-deploy": "CI/CD: from commit to deploy, explained",
    "kubernetes-pods-services-why-exist": "Kubernetes: pods, services, and why",
    "iam-mistakes-beginner-cloud-incidents": "IAM mistakes behind beginner cloud incidents",
    "devops-interview-systems-thinking": "DevOps interviews: showing systems thinking",
    "reading-cloud-bills-logs-costs": "Reading cloud bills when costs spike",
    "manual-to-automation-skills-transfer": "Manual to automation: skills that transfer",
    "selenium-locators-survive-ui-changes": "Selenium locators that survive UI changes",
    "bug-reports-developers-act-on": "Bug reports developers act on, first time",
    "test-planning-release-coverage": "Test planning: coverage without pretending",
    "qa-interview-questions-thinking": "QA interview questions that test thinking",
    "reconciliation-breaks-records-disagree": "Reconciliation breaks: why records disagree",
    "accounts-payable-three-way-match": "Accounts payable: the three-way match",
    "accounts-receivable-ageing-who-owes": "Accounts receivable ageing: who owes what",
    "payroll-inputs-data-right-before-payday": "Payroll inputs: getting the data right",
    "treasury-basics-cash-positioning": "Treasury basics: cash positioning, plainly",
    "fund-accounting-nav-daily-activity": "Fund accounting: how NAV gets built daily",
    "invoice-exceptions-stall-payments": "Invoice exceptions that stall payments",
    "month-end-close-checklists": "Month-end close checklists that save panic",
    "bank-reconciliations-statements-ledger": "Bank reconciliations: statements to ledger",
    "finance-operations-interview-process-questions": "Finance operations interviews: what to expect",
    "bpo-to-compliance-mapping-skills": "From BPO to compliance: mapping your skills",
    "starting-fresh-after-graduation-no-experience": "Starting fresh after graduation, no experience",
    "changing-fields-at-thirty-plan": "Changing fields at thirty: a realistic plan",
    "no-degree-routes-operations-roles": "No degree? Routes into operations roles",
    "customer-support-to-it-bridge": "From customer support to IT: the bridge",
    "choosing-between-two-career-paths": "Choosing between two career paths",
    "gap-year-build-proof": "Using a gap year to build proof",
    "moving-cities-for-job-questions": "Moving cities for a job: what to settle first",
    "when-short-course-worth-it": "When a short course is worth it",
    "re-entering-work-after-break-routine": "Re-entering work after a break: a routine",
    "resume-bullets-show-what-changed": "Resume bullets that show what changed",
    "technical-rounds-thinking-aloud": "Technical rounds: thinking aloud, clearly",
    "salary-discussions-without-number-first": "Salary talks without quoting a number first",
    "follow-up-emails-after-interview": "Follow-up emails that keep you visible",
    "group-discussions-contributing": "Group discussions: contributing well",
    "explaining-failed-interview-usefully": "Explaining a failed interview, usefully",
    "resume-formatting-screening-software": "Resume formatting that survives screening",
    "questions-to-ask-interviewer-real-job": "Questions that reveal the real job",
    "two-offers-comparing-beyond-headline": "Two offers: comparing beyond the headline",
    "using-jobs-board-filters-save-hours": "Using a jobs board well: filters that help",
    "applying-smartly-fewer-better-fit": "Apply smartly: fewer applications, better fit",
    "offer-letters-clauses-before-sign": "Offer letters: clauses to read before signing",
    "first-ninety-days-learning-team": "Your first ninety days: learn the team first",
    "referrals-asking-without-awkward": "Referrals: asking without being awkward",
    "stop-applying-start-preparing": "When to stop applying and start preparing",
    "remote-job-listings-checking-real": "Remote job listings: checking they are real",
}

# file -> [(old, new, expected_count)] ; expected_count None = any>=1
EDITS = {
    "styles.css": [
        (".post-body h3{font-size:21px;margin:30px 0 12px}",
         ".post-body h2{font-size:21px;margin:30px 0 12px}\n"
         ".legal h2{font-size:21px;margin:28px 0 8px}", 1),
        (".foot-col h4{font:700 15px var(--font-b);color:var(--amber);margin-bottom:14px}",
         ".foot-col h2{font:700 15px var(--font-b);color:var(--amber);margin-bottom:14px}", 1),
    ],
    "home.css": [
        (".persona h3{", ".persona h2{", 1),
        (".demo-card h3{", ".demo-card h2{", 1),
        (".online-card h3{", ".online-card h2{", 1),
        (".ait-card h3{", ".ait-card h2{", 1),
        (".aa-jobline h4{", ".aa-jobline h3{", 1),
        (".aa-kw h5{", ".aa-kw h4{", 1),
    ],
    "jobs.html": [
        (".snap-head h3{", ".snap-head h2{", 1),
        (".bc-job h4{", ".bc-job h3{", 1),
        ("<h3>Board snapshot</h3>", "<h2>Board snapshot</h2>", 1),
        ("<h4>Lead - Partner Onboarding &amp; Due Diligence</h4>",
         "<h3>Lead - Partner Onboarding &amp; Due Diligence</h3>", 1),
        ("<h4>Global Sanctions and SWIFT Utility Delivery Lead</h4>",
         "<h3>Global Sanctions and SWIFT Utility Delivery Lead</h3>", 1),
        ("<h4>Team Leader, KYC Operations</h4>",
         "<h3>Team Leader, KYC Operations</h3>", 1),
        ("<h4>KYC Analyst</h4>", "<h3>KYC Analyst</h3>", 1),
    ],
    "apply.html": [
        (".aa-visual .v-head h3{", ".aa-visual .v-head h2{", 1),
        (".aa-visual .v-kw h4{", ".aa-visual .v-kw h3{", 1),
        (".ats-check h4{", ".ats-check h3{", 1),
        ("<div><h3>AML/KYC Analyst</h3>", "<div><h2>AML/KYC Analyst</h2>", 1),
        ("<h4>Keywords in your profile</h4>",
         "<h3>Keywords in your profile</h3>", 1),
        ('<h4 style="margin-top:12px">Missing — learn or confirm</h4>',
         '<h3 style="margin-top:12px">Missing — learn or confirm</h3>', 1),
        ("<h4>ATS checklist — is this resume ready to send?</h4>",
         "<h3>ATS checklist — is this resume ready to send?</h3>", 1),
    ],
    "index.html": [
        ("<h3>Book your free demo class</h3>",
         "<h2>Book your free demo class</h2>", 1),
    ],
    "ai-tools.html": [
        ("<h3>Apply Assistant</h3>", "<h2>Apply Assistant</h2>", 1),
        ("<h3>Resume Evaluator</h3>", "<h2>Resume Evaluator</h2>", 1),
        ("<h3>Socrates · Interview Coach</h3>",
         "<h2>Socrates · Interview Coach</h2>", 1),
        ("<h3>Skill Gap Planner</h3>", "<h2>Skill Gap Planner</h2>", 1),
        ("<div><h4>AML/KYC Analyst</h4>", "<div><h3>AML/KYC Analyst</h3>", 1),
        ("<h5>Already in the resume</h5>", "<h4>Already in the resume</h4>", 1),
        ("<h5>Missing from the job description</h5>",
         "<h4>Missing from the job description</h4>", 1),
    ],
    "courses.html": [
        ("<h3>Fresh graduate</h3>", "<h2>Fresh graduate</h2>", 1),
        ("<h3>Switching careers, no coding</h3>",
         "<h2>Switching careers, no coding</h2>", 1),
        ("<h3>Commerce &amp; finance background</h3>",
         "<h2>Commerce &amp; finance background</h2>", 1),
        ("<h3>IT, support &amp; operations</h3>",
         "<h2>IT, support &amp; operations</h2>", 1),
        ("<h3>Want to build &amp; code</h3>", "<h2>Want to build &amp; code</h2>", 1),
    ],
    "how-it-works.html": [
        ("<h3>Live mentor-led classes</h3>", "<h2>Live mentor-led classes</h2>", 1),
        ("<h3>AI-led curriculum</h3>", "<h2>AI-led curriculum</h2>", 1),
        ("<h3>AI mock interviews, scored</h3>",
         "<h2>AI mock interviews, scored</h2>", 1),
        ("<h3>Resumes rebuilt by AI</h3>", "<h2>Resumes rebuilt by AI</h2>", 1),
        ("<h3>Proof from the live board</h3>",
         "<h2>Proof from the live board</h2>", 1),
    ],
    "faq.html": [
        ("<h3>100% online, from anywhere in India</h3>",
         "<h2>100% online, from anywhere in India</h2>", 1),
    ],
    "fees.html": [
        ("<title>Fees | NaukriSala — Start with ₹15,000. Rest after placement.</title>",
         "<title>Fees — ₹15,000 upfront, rest after placement | NaukriSala</title>", 1),
        ('content="Fees | NaukriSala — Start with ₹15,000. Rest after placement."',
         'content="Fees — ₹15,000 upfront, rest after placement | NaukriSala"', None),
    ],
    "naukrisala-vs-career-cracker.html": [
        ("<title>NaukriSala vs Career Cracker | Compare fees, format and placement support</title>",
         "<title>NaukriSala vs Career Cracker: fees, format, placement</title>", 1),
        ('content="NaukriSala vs Career Cracker | Compare fees, format and placement support"',
         'content="NaukriSala vs Career Cracker: fees, format, placement"', None),
    ],
    "placement-courses-bhubaneswar.html": [
        ("<title>Placement courses in Bhubaneswar | NaukriSala — 100% online, pay after placement</title>",
         "<title>Placement courses in Bhubaneswar | NaukriSala</title>", 1),
        ('content="Placement courses in Bhubaneswar | NaukriSala — 100% online, pay after placement"',
         'content="Placement courses in Bhubaneswar | NaukriSala"', None),
    ],
    "tools/generate_blog.py": [
        ("<h4>Top courses</h4>", "<h2>Top courses</h2>", 1),
        ("<h4>AI tools</h4>", "<h2>AI tools</h2>", 1),
        ("<h4>Company</h4>", "<h2>Company</h2>", 1),
        ("<h4>Contact</h4>", "<h2>Contact</h2>", 1),
    ],
}

FOOTER_HEADS = ["Top courses", "AI tools", "Company", "Contact"]


def replace(path, old, new, expect=None):
    full = os.path.join(ROOT, path)
    s = open(full, encoding="utf-8").read()
    n = s.count(old)
    if expect is not None and n != expect:
        raise SystemExit(f"{path}: expected {expect}x {old[:50]!r}, found {n}x")
    if n == 0:
        raise SystemExit(f"{path}: not found: {old[:60]!r}")
    if not DRY:
        open(full, "w", encoding="utf-8").write(s.replace(old, new))
    print(f"  {path}: {n}x {old[:52]!r} -> {new[:52]!r}")


def main():
    # 0. sanity: every new title fits
    for slug, t in TITLE_MAP.items():
        assert len(t) <= 47, (slug, t, len(t))
        assert len(t) + len(" | NaukriSala") <= 60, slug
    print(f"titles: {len(TITLE_MAP)} rewrites, all <=47 chars")

    # A. CSS retargets + D/E page edits
    for path, edits in EDITS.items():
        print(f"-- {path}")
        for old, new, expect in edits:
            replace(path, old, new, expect)

    # B. footer h4 -> h2 in every html file (root + blog twins)
    print("-- footer h4 -> h2 (all html files)")
    total = 0
    for f in sorted(glob.glob(os.path.join(ROOT, "*.html")) +
                    glob.glob(os.path.join(ROOT, "blog", "*.html"))):
        s = open(f, encoding="utf-8").read()
        changed = False
        for h in FOOTER_HEADS:
            old, new = f"<h4>{h}</h4>", f"<h2>{h}</h2>"
            if s.count(old):
                assert s.count(old) == 1, (f, h, s.count(old))
                s = s.replace(old, new)
                changed = True
                total += 1
        if changed and not DRY:
            open(f, "w", encoding="utf-8").write(s)
    print(f"  footer headings changed: {total} (expect 124 files x 4 = 496)")

    # C. posts.js: titles + body h3 -> h2
    print("-- posts.js")
    p = os.path.join(ROOT, "posts.js")
    s = open(p, encoding="utf-8").read()
    for slug, new in TITLE_MAP.items():
        m = re.search(re.escape(f'slug: "{slug}"') +
                      r".{0,200}?title: \"([^\"]+)\"", s, re.S)
        assert m, f"title not found for {slug}"
        old = m.group(1)
        assert s.count(f'title: "{old}"') == 1, (slug, old)
        s = s.replace(f'title: "{old}"', f'title: "{new}"')
    assert s.count("<h3>") == 100 and s.count("</h3>") == 100, \
        (s.count("<h3>"), s.count("</h3>"))
    s = s.replace("<h3>", "<h2>").replace("</h3>", "</h2>")
    if not DRY:
        open(p, "w", encoding="utf-8").write(s)
    print(f"  {len(TITLE_MAP)} titles rewritten; 100 body h3 -> h2")

    # D. privacy/terms: h3 -> h2 + .legal container (inline margins move to CSS)
    print("-- privacy.html / terms.html")
    for fname in ("privacy.html", "terms.html"):
        full = os.path.join(ROOT, fname)
        s = open(full, encoding="utf-8").read()
        heads = re.findall(r'<h3 style="margin:28px 0 8px">([^<]+)</h3>', s)
        assert heads, fname
        for h in heads:
            old = f'<h3 style="margin:28px 0 8px">{h}</h3>'
            assert s.count(old) == 1, (fname, h)
            s = s.replace(old, f"<h2>{h}</h2>")
        old_wrap = '<section class="section">\n    <div class="wrap">'
        assert s.count(old_wrap) == 1, fname
        s = s.replace(old_wrap,
                      '<section class="section">\n    <div class="wrap legal">')
        if not DRY:
            open(full, "w", encoding="utf-8").write(s)
        print(f"  {fname}: {len(heads)} h3 -> h2, .legal container added")

    print("DONE" + (" (dry run — nothing written)" if DRY else ""))


if __name__ == "__main__":
    main()
