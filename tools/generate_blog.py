"""Generate NaukriSala blog: blog.html index + blog/<slug>.html x100 from posts.js.
Source of truth: posts.js (NS_POSTS). Re-run after any template change.
Usage: python3 tools/generate_blog.py  (run from the repo root)"""
import json, subprocess, html, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
out = subprocess.run(['node', '-e',
    "const fs=require('fs');let src=fs.readFileSync('posts.js','utf8').replace('const NS_POSTS','NS_POSTS');eval(src);console.log(JSON.stringify(NS_POSTS))"],
    capture_output=True, text=True, check=True)
POSTS = json.loads(out.stdout)
assert len(POSTS) == 100, len(POSTS)
assert len({p['slug'] for p in POSTS}) == 100
TRACKS = ["AML & KYC","ServiceNow","STOM","Data Science & AI","Full Stack Python",
          "Cloud & DevOps","Testing","Finance Operations","Career Change",
          "Interviews & Resume","Jobs & Placement"]
assert sorted({p['track'] for p in POSTS}) == sorted(TRACKS)

def chrome(prefix):
    """Site chrome (topbar/nav/footer) with path prefix '' (root) or '../' (blog/)."""
    nav = f"""<div class="topbar"><b>Batch 9 starts 10 Nov 2026</b> &nbsp;·&nbsp; Free demos from 3 Nov</div>

<header class="nav" id="nav">
  <div class="wrap nav-inner">
    <a class="brand" href="{prefix}index.html">
      <img class="brand-mark-img" src="{prefix}assets/brand/ns-logo-blue.png" alt="NaukriSala logo">
      <span class="brand-word">naukrisala<span class="brand-dot">.</span></span>
    </a>
    <nav class="nav-links" id="navLinks">
      <a href="{prefix}courses.html">Courses</a>
      <a href="{prefix}how-it-works.html">How it works</a>
      <a href="{prefix}fees.html">Fees</a>
      <a href="{prefix}jobs.html">Jobs</a>
      <a href="{prefix}ai-tools.html">AI Tools</a>
      <a href="{prefix}faq.html">FAQ</a>
      <a href="{prefix}blog.html">Blog</a>
    </nav>
    <div class="nav-cta">
      <a class="btn btn-primary btn-sm" href="{prefix}index.html#demo">Book free demo <span class="arr">→</span></a>
      <button class="nav-toggle" id="navToggle" aria-label="Menu">☰</button>
    </div>
  </div>
</header>"""
    foot = f"""<footer class="footer">
  <div class="wrap footer-grid">
    <div class="foot-brand">
      <a class="brand" href="{prefix}index.html">
        <img class="brand-mark-img" src="{prefix}assets/brand/ns-logo-blue.png" alt="NaukriSala logo">
        <span class="brand-word">naukrisala<span class="brand-dot">.</span></span>
      </a>
      <div class="foot-social">
        <a href="#" aria-label="Social link 1 — coming soon" title="Coming soon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg></a>
        <a href="#" aria-label="Social link 2 — coming soon" title="Coming soon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg></a>
        <a href="#" aria-label="Social link 3 — coming soon" title="Coming soon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg></a>
      </div>
      <p class="fine">Get placed first. Pay from your salary.</p>
      <a class="foot-cta" href="{prefix}index.html#demo">Book a free demo <span class="arr">→</span></a>
      <p class="foot-cta-sub">Batch 9 starts 10 Nov 2026 · Free demos from 3 Nov</p>
    </div>
    <nav class="foot-col">
      <h4>Top courses</h4>
      <a href="{prefix}course-aml-kyc.html">AML &amp; KYC</a>
      <a href="{prefix}course-servicenow.html">ServiceNow</a>
      <a href="{prefix}course-stom.html">STOM</a>
      <a href="{prefix}course-data-science-ai.html">Data Science &amp; AI</a>
      <a href="{prefix}course-full-stack-python.html">Full Stack Python</a>
      <a href="{prefix}courses.html">All courses</a>
    </nav>
    <nav class="foot-col">
      <h4>AI tools</h4>
      <a href="{prefix}socrates.html">AI Interview Coach</a>
      <a href="{prefix}resume-evaluator.html">Resume Evaluator</a>
      <a href="{prefix}skill-gap.html">Skill Gap</a>
      <a href="{prefix}apply.html">Apply Assistant</a>
    </nav>
    <nav class="foot-col">
      <h4>Company</h4>
      <a href="{prefix}how-it-works.html">How it works</a>
      <a href="{prefix}fees.html">Fees</a>
      <a href="{prefix}jobs.html">Jobs</a>
      <a href="{prefix}faq.html">FAQ</a>
      <a href="{prefix}track-record.html">Track record</a>
      <a href="{prefix}blog.html">Blog</a>
      <a href="{prefix}terms.html">Terms</a>
      <a href="{prefix}privacy.html">Privacy</a>
    </nav>
    <div class="foot-col">
      <h4>Contact</h4>
      <a href="tel:+918450049035">+91 84500 49035</a>
      <a href="https://wa.me/918450049035">Chat on WhatsApp</a>
    </div>
  </div>
  <div class="wrap foot-bar">
    <p>© 2026 NaukriSala. All rights reserved.</p>
  </div>
</footer>

<a class="wa-float" id="waFloat" href="#" aria-label="Chat on WhatsApp"></a>
<script src="{prefix}script.js"></script>
<script src="{prefix}maya.js?v=20261026n1"></script>"""
    return nav, foot

def head(title, desc, canon, prefix):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)} | NaukriSala</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="https://lunasticgold-hub.github.io/naukrisala/{canon}">
<meta property="og:title" content="{html.escape(title)} | NaukriSala">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="https://lunasticgold-hub.github.io/naukrisala/{canon}">
<meta property="og:image" content="https://lunasticgold-hub.github.io/naukrisala/assets/brand/ns-logo-blue.png">
<meta property="og:site_name" content="NaukriSala">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{html.escape(title)} | NaukriSala">
<meta name="twitter:description" content="{html.escape(desc)}">
<meta name="twitter:image" content="https://lunasticgold-hub.github.io/naukrisala/assets/brand/ns-logo-blue.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{prefix}styles.css?v=20261025n11">
<link rel="stylesheet" href="{prefix}home.css?v=20261025n9">
<link rel="stylesheet" href="{prefix}maya.css?v=20261026n1">
<link rel="icon" type="image/png" href="{prefix}assets/brand/ns-logo-blue.png">
</head>
<body>
"""

# ---------- blog.html ----------
nav, foot = chrome('')
filters = '<button class="blog-filter active" data-track="all">All topics</button>' + ''.join(
    f'<button class="blog-filter" data-track="{html.escape(t)}">{html.escape(t)}</button>' for t in TRACKS)
cards = '\n'.join(
    f'      <article class="blog-card" data-track="{html.escape(p["track"])}"><span class="blog-tag">{html.escape(p["track"])}</span><h3><a href="blog/{p["slug"]}.html">{html.escape(p["title"])}</a></h3><p>{html.escape(p["excerpt"])}</p><span class="blog-read">{p["read"]} min read</span></article>'
    for p in POSTS)
blog_html = head('Blog', 'Practical guides for the careers NaukriSala trains for — compliance, ServiceNow, data, cloud, and the job hunt itself.', 'blog.html', '') + nav + f"""
<main>
  <section class="section">
    <div class="wrap">
      <div class="sec-head">
        <p class="eyebrow"><span class="dot"></span>Blog</p>
        <h2>The NaukriSala blog.</h2>
        <p class="lede-sm">Practical guides for the careers we train for — compliance, ServiceNow, data, cloud, and the job hunt itself. No fluff, no fake promises.</p>
      </div>
      <div class="blog-filters">{filters}</div>
      <div class="blog-grid">
{cards}
      </div>
    </div>
  </section>
</main>

""" + foot + """
<script>
var TRACK_BY_HASH = {"aml-kyc":"AML & KYC","servicenow":"ServiceNow","stom":"STOM","data-science-ai":"Data Science & AI","full-stack-python":"Full Stack Python","cloud-devops":"Cloud & DevOps","testing":"Testing","finance-operations":"Finance Operations","career-change":"Career Change","interviews-resume":"Interviews & Resume","jobs-placement":"Jobs & Placement"};
function applyFilter(t){
  document.querySelectorAll('.blog-filter').forEach(function(b){b.classList.toggle('active', b.getAttribute('data-track') === t)});
  document.querySelectorAll('.blog-card').forEach(function(c){
    c.style.display = (t === 'all' || c.getAttribute('data-track') === t) ? '' : 'none';
  });
}
document.querySelectorAll('.blog-filter').forEach(function(btn){
  btn.addEventListener('click', function(){ applyFilter(btn.getAttribute('data-track')); });
});
var h = window.location.hash.replace('#','');
if (TRACK_BY_HASH[h]) applyFilter(TRACK_BY_HASH[h]);
</script>
</body>
</html>
"""
open('blog.html', 'w', encoding='utf-8').write(blog_html)

# ---------- post pages ----------
nav2, foot2 = chrome('../')
os.makedirs('blog', exist_ok=True)
RELATED = {
  "AML & KYC": [("AML & KYC course", "../course-aml-kyc.html"), ("Jobs board", "../jobs.html")],
  "ServiceNow": [("ServiceNow course", "../course-servicenow.html"), ("Jobs board", "../jobs.html")],
  "STOM": [("STOM course", "../course-stom.html"), ("Jobs board", "../jobs.html")],
  "Data Science & AI": [("Data Science & AI course", "../course-data-science-ai.html"), ("Jobs board", "../jobs.html")],
  "Full Stack Python": [("Full Stack Python course", "../course-full-stack-python.html"), ("Jobs board", "../jobs.html")],
  "Cloud & DevOps": [("All courses", "../courses.html"), ("Jobs board", "../jobs.html")],
  "Testing": [("All courses", "../courses.html"), ("Jobs board", "../jobs.html")],
  "Finance Operations": [("All courses", "../courses.html"), ("Jobs board", "../jobs.html")],
  "Career Change": [("All courses", "../courses.html"), ("Placement stories", "../track-record.html")],
  "Interviews & Resume": [("Jobs board", "../jobs.html"), ("Apply Assistant", "../apply.html")],
  "Jobs & Placement": [("Jobs board", "../jobs.html"), ("All courses", "../courses.html")],
}
for p in POSTS:
    rel_html = '<div class="related-links"><span>Related:</span> ' + ' \u00b7 '.join('<a href="' + u + '">' + t + '</a>' for t, u in RELATED[p['track']]) + '</div>'
    page = head(p['title'], p['excerpt'], f"blog/{p['slug']}.html", '../') + nav2 + f"""
<main>
  <section class="section">
    <div class="wrap post-wrap">
      <p class="eyebrow"><span class="dot"></span>{html.escape(p['track'])}</p>
      <h1>{html.escape(p['title'])}</h1>
      <p class="blog-read">{p['read']} min read</p>
      <div class="post-body">{p['body']}</div>
      {rel_html}
      <div class="post-foot">
        <a class="link-arrow" href="../blog.html">&larr; Back to the blog</a>
        <a class="btn btn-primary" href="../index.html#demo">Book a free demo <span class="arr">→</span></a>
      </div>
    </div>
  </section>
</main>

""" + foot2 + """
</body>
</html>
"""
    open(f"blog/{p['slug']}.html", 'w', encoding='utf-8').write(page)
print('generated blog.html +', len(POSTS), 'post pages')
