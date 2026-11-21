"""Related Pages component — single source of truth for the "Keep exploring"
section at the end of content pages (redesigned 2026-11-22).

What it replaces: the old `<div class="related-links"><span>Related:</span>
...` pill strips, which were hardcoded per template and identical in shape
on every page.

Design rules (enforced by render_related, not by convention):
- Links are chosen from page metadata (type, track/course), never hardcoded
  per page in the templates. To cover a new page, add one entry to
  PAGE_RELATED; to cover a new dedicated course page, add one entry to
  COURSES (its course page, jobs and fees links follow automatically).
- Only pages that actually exist are linked (checked against the repo).
- The current page is never linked, and no link repeats.
- At most 6 links per page; fewer when fewer are relevant — never padded
  with irrelevant destinations.
- Blog posts get two groups: same-track guides first, then the track's
  course/jobs pages. Hand-written pages get the groups in PAGE_RELATED.
- Output is static HTML (good for SEO/internal linking — never JS-injected).
- Placement: on hand-written pages the section sits inside a
  <div class="wrap"> (added 2026-11-22 after the visual check caught the
  course pages rendering full-bleed, edge to edge). apply_related.py
  replaces only the <section>, so the wrap survives re-runs; blog posts
  sit inside .post-wrap instead. Never render the section as a direct
  child of <main> — it spans the full viewport width.

Hrefs are stored root-relative (e.g. "jobs", "blog#aml-kyc"); render adds
the "../" prefix on blog post pages. Labels are plain text, escaped on render.
"""

import html as htmlmod
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MAX_LINKS = 6

# --- dedicated course pages: slug -> track + blog filter hash + page --------
# The 5 courses with their own page. The other 10 courses have no dedicated
# page, so their guides point at the course listing instead.
COURSES = {
    "aml-kyc": {"track": "AML & KYC", "track_hash": "aml-kyc",
                "page": "course-aml-kyc"},
    "servicenow": {"track": "ServiceNow", "track_hash": "servicenow",
                   "page": "course-servicenow"},
    "stom": {"track": "STOM", "track_hash": "stom", "page": "course-stom"},
    "data-science-ai": {"track": "Data Science & AI",
                        "track_hash": "data-science-ai",
                        "page": "course-data-science-ai"},
    "full-stack-python": {"track": "Full Stack Python",
                          "track_hash": "full-stack-python",
                          "page": "course-full-stack-python"},
}

# --- blog post "explore further" group, keyed by track -----------------------
# A track with a dedicated course page points at it; the rest point at the
# course listing. Values preserved from the pre-redesign map — only the
# presentation changed.
BLOG_GROUPS = {
    "AML & KYC": ("Courses & jobs", [("AML & KYC course", "course-aml-kyc"),
                                     ("Jobs board", "jobs")]),
    "ServiceNow": ("Courses & jobs", [("ServiceNow course", "course-servicenow"),
                                      ("Jobs board", "jobs")]),
    "STOM": ("Courses & jobs", [("STOM course", "course-stom"),
                                ("Jobs board", "jobs")]),
    "Data Science & AI": ("Courses & jobs",
                          [("Data Science & AI course", "course-data-science-ai"),
                           ("Jobs board", "jobs")]),
    "Full Stack Python": ("Courses & jobs",
                          [("Full Stack Python course", "course-full-stack-python"),
                           ("Jobs board", "jobs")]),
    "Cloud & DevOps": ("Courses & jobs", [("All courses", "courses"),
                                          ("Jobs board", "jobs")]),
    "Testing": ("Courses & jobs", [("All courses", "courses"),
                                   ("Jobs board", "jobs")]),
    "Finance Operations": ("Courses & jobs", [("All courses", "courses"),
                                              ("Jobs board", "jobs")]),
    "Career Change": ("Courses & stories", [("All courses", "courses"),
                                            ("Placement stories", "track-record")]),
    "Interviews & Resume": ("Jobs & tools", [("Jobs board", "jobs"),
                                             ("Apply Assistant", "apply")]),
    "Jobs & Placement": ("Courses & jobs", [("Jobs board", "jobs"),
                                            ("All courses", "courses")]),
}


def related_for_post(post, posts):
    """Groups for one blog post: same-track guides first (max 3), then the
    track's course/jobs pages. `post`/`posts` are posts.js entries."""
    track = post["track"]
    same = [q for q in posts if q["track"] == track and q["slug"] != post["slug"]]
    other = [q for q in posts if q["track"] != track and q["slug"] != post["slug"]]
    chosen = (same + other)[:3]
    groups = []
    if chosen:
        groups.append((f"More {track} guides",
                       [(q["title"], "blog/" + q["slug"]) for q in chosen]))
    label, links = BLOG_GROUPS.get(
        track, ("Courses & jobs", [("All courses", "courses"),
                                   ("Jobs board", "jobs")]))
    groups.append((label, links))
    return groups


# --- hand-written pages: file name -> [(group label or None, [(text, href)])]
# A None label (single-group pages) renders no sub-heading — just the list
# under "Keep exploring".
PAGE_RELATED = {
    "courses.html": [
        ("Guides & stories", [("Career guides on the blog", "blog"),
                              ("Placement stories", "track-record")]),
        ("Jobs & comparison", [("Live openings", "jobs"),
                               ("NaukriSala vs Career Cracker",
                                "naukrisala-vs-career-cracker")]),
    ],
    "jobs.html": [
        ("Guides & courses", [("Job-hunt guides", "blog#jobs-placement"),
                              ("Courses", "courses"),
                              ("Placement stories", "track-record")]),
        ("Application tools", [("Apply Assistant", "apply"),
                               ("Resume Evaluator", "resume-evaluator")]),
    ],
    "apply.html": [
        ("Jobs & guides", [("Jobs board", "jobs"),
                           ("Interview & resume guides",
                            "blog#interviews-resume")]),
        ("More tools", [("Resume Evaluator", "resume-evaluator"),
                        ("Skill Gap", "skill-gap"),
                        ("AI Interview Coach", "socrates")]),
    ],
    "skill-gap.html": [
        ("Next steps", [("Courses", "courses"), ("Jobs board", "jobs")]),
        ("More tools & guides", [("AI Interview Coach", "socrates"),
                                 ("Career guides", "blog")]),
    ],
    "fees.html": [
        ("Learn more", [("How it works", "how-it-works"), ("FAQ", "faq")]),
        ("Compare & explore", [("Courses", "courses"),
                               ("NaukriSala vs Career Cracker",
                                "naukrisala-vs-career-cracker")]),
    ],
    "track-record.html": [
        (None, [("Jobs board", "jobs"), ("Courses", "courses"),
                ("Blog", "blog")]),
    ],
    "ai-tools.html": [
        (None, [("Blog", "blog"), ("Courses", "courses"),
                ("Jobs board", "jobs")]),
    ],
    "faq.html": [
        (None, [("Fees", "fees"), ("How it works", "how-it-works"),
                ("Blog", "blog")]),
    ],
    "how-it-works.html": [
        (None, [("Fees", "fees"), ("Courses", "courses"),
                ("Blog", "blog")]),
    ],
    "naukrisala-vs-career-cracker.html": [
        ("Learn more", [("How it works", "how-it-works"), ("FAQ", "faq")]),
        ("Courses & fees", [("All courses", "courses"), ("Fees", "fees")]),
    ],
    "placement-courses-bhubaneswar.html": [
        ("Courses & jobs", [("All courses", "courses"),
                            ("Live openings", "jobs")]),
        ("Learn more", [("Fees", "fees"), ("How it works", "how-it-works")]),
    ],
    "resume-evaluator.html": [
        ("Jobs & guides", [("Jobs board", "jobs"),
                           ("Interview & resume guides",
                            "blog#interviews-resume")]),
        ("More tools", [("Apply Assistant", "apply"),
                        ("Skill Gap", "skill-gap")]),
    ],
    "socrates.html": [
        ("Guides & courses", [("Interview & resume guides",
                               "blog#interviews-resume"),
                              ("Courses", "courses")]),
        ("More tools", [("Apply Assistant", "apply"),
                        ("Resume Evaluator", "resume-evaluator")]),
    ],
}

# Course pages follow one rule each: their track's guides, then jobs, the
# course listing and the fees page (enrolment). Built from COURSES so a new
# dedicated course page is covered by adding one COURSES entry.
for _slug, _c in COURSES.items():
    PAGE_RELATED[_c["page"] + ".html"] = [
        ("Guides", [(f"{_c['track']} guides", "blog#" + _c["track_hash"])]),
        ("Courses & enrolment", [("Jobs board", "jobs"),
                                 ("All courses", "courses"),
                                 ("Fees & enrolment", "fees")]),
    ]


def _target_exists(href):
    """Does the link target exist in the repo? href is root-relative, may
    carry a #fragment (blog#aml-kyc -> blog.html)."""
    path = href.split("#", 1)[0]
    if not path or path.startswith("http"):
        return bool(path)
    return (os.path.exists(os.path.join(ROOT, path + ".html"))
            or os.path.exists(os.path.join(ROOT, path)))


def render_related(groups, prefix="", current="", indent=""):
    """Render the <section class="related"> for `groups`.

    groups: [(group label or None, [(link text, root-relative href), ...])]
    prefix: "" on root pages, "../" on blog post pages.
    current: root-relative path of the page itself, without ".html"
        (e.g. "jobs", "course-aml-kyc", "blog/<slug>") — never linked.
    indent: leading whitespace for every emitted line (keeps files tidy).
    Returns "" when no link survives the checks.
    """
    seen = set()
    total = 0
    out_groups = []
    for label, links in groups:
        kept = []
        for text, href in links:
            if total >= MAX_LINKS:
                break
            if href.split("#", 1)[0] == current:
                continue
            if href in seen:
                continue
            if not _target_exists(href):
                continue
            seen.add(href)
            kept.append((text, prefix + href))
            total += 1
        if kept:
            out_groups.append((label, kept))
    if not out_groups:
        return ""
    multi = len(out_groups) > 1
    lines = ['<section class="related" aria-label="Related pages">',
             '<h2 class="related-label">Keep exploring</h2>']
    for label, links in out_groups:
        lines.append('<div class="related-group">')
        if multi and label:
            lines.append('<h3 class="related-group-label">'
                         + htmlmod.escape(label) + '</h3>')
        lines.append('<ul class="related-list">')
        for text, href in links:
            lines.append('<li><a href="' + htmlmod.escape(href, quote=True)
                         + '"><span>' + htmlmod.escape(text) + '</span>'
                         + '<span class="related-arrow" aria-hidden="true">'
                         + '\u2192</span></a></li>')
        lines.append('</ul>')
        lines.append('</div>')
    lines.append('</section>')
    if indent:
        lines = [(indent + ln) if ln else ln for ln in lines]
    return "\n".join(lines)
