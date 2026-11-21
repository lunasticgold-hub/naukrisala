"""Generate NaukriSala blog: blog.html index + blog/<slug>.html x100 from posts.js.
Source of truth: posts.js (NS_POSTS). Re-run after any template change.
Usage: python3 tools/generate_blog.py  (run from the repo root)

The "Keep exploring" section at the end of each post comes from
tools/related.py (related_for_post + render_related) — the single source of
truth for related links across the whole site."""
import json, subprocess, html, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from related import related_for_post, render_related

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
out = subprocess.run(['node', '-e',
    "const fs=require('fs');let src=fs.readFileSync('posts.js','utf8').replace('const NS_POSTS','NS_POSTS');eval(src);console.log(JSON.stringify(NS_POSTS))"],
    capture_output=True, text=True, check=True)
POSTS = json.loads(out.stdout)
assert len(POSTS) >= 100, len(POSTS)
assert len({p['slug'] for p in POSTS}) == len(POSTS)
TRACKS = ["AML & KYC","ServiceNow","STOM","Data Science & AI","Full Stack Python",
          "Cloud & DevOps","Testing","Finance Operations","Career Change",
          "Interviews & Resume","Jobs & Placement"]
assert sorted({p['track'] for p in POSTS}) == sorted(TRACKS)

def chrome(prefix):
    """Site chrome (topbar/nav/footer) with path prefix '' (root) or '../' (blog/)."""
    home = '../' if prefix == '../' else './'
    nav = f"""<div class="topbar"><b>AML &amp; KYC Batch 9 begins 10 Jan 2027</b> &nbsp;·&nbsp; Free Demo Classes from 2–7 Jan &nbsp;·&nbsp; Enrolments Open</div>

<header class="nav" id="nav">
  <div class="wrap nav-inner">
    <a class="brand" href="{home}">
      <img class="brand-mark-img" src="{prefix}assets/brand/ns-logo-blue.png" alt="NaukriSala logo">
      <span class="brand-word">naukrisala<span class="brand-dot">.</span></span>
    </a>
    <nav class="nav-links" id="navLinks">
      <a href="{prefix}courses">Courses</a>
      <a href="{prefix}how-it-works">How it works</a>
      <a href="{prefix}fees">Fees</a>
      <a href="{prefix}jobs">Jobs</a>
      <a href="{prefix}ai-tools">AI Tools</a>
      <a href="{prefix}faq">FAQ</a>
      <a href="{prefix}blog">Blog</a>
    </nav>
    <div class="nav-cta">
      <a class="btn btn-primary btn-sm" href="{home}#demo">Book free demo <span class="arr">→</span></a>
      <button type="button" class="nav-toggle" id="navToggle" aria-label="Menu">☰</button>
    </div>
  </div>
</header>"""
    foot = f"""<footer class="footer">
  <div class="wrap footer-grid">
    <div class="foot-brand">
      <a class="brand" href="{home}">
        <img class="brand-mark-img" src="{prefix}assets/brand/ns-logo-blue.png" alt="NaukriSala logo">
        <span class="brand-word">naukrisala<span class="brand-dot">.</span></span>
      </a>
      <div class="foot-social">
        <a class="soc-x" href="https://x.com/Naukrisala?s=20" target="_blank" rel="noopener" aria-label="NaukriSala on X" title="NaukriSala on X"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg></a>
        <a class="soc-li" href="https://www.linkedin.com/company/naukrysala-academy/home/?viewAsMember=true" target="_blank" rel="noopener" aria-label="NaukriSala on LinkedIn" title="NaukriSala on LinkedIn"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.225 0z"/></svg></a>
        <a class="soc-ig" href="https://www.instagram.com/naukrisala/" target="_blank" rel="noopener" aria-label="NaukriSala on Instagram" title="NaukriSala on Instagram"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/></svg></a>
      </div>
      <p class="fine">Get placed first. Pay from your salary.</p>
      <a class="foot-cta" href="{home}#demo">Book a free demo <span class="arr">→</span></a>
      <p class="foot-cta-sub">AML &amp; KYC Batch 9 begins 10 Jan 2027 · Free Demo Classes from 2–7 Jan · Enrolments Open</p>
    </div>
    <nav class="foot-col">
      <h2>Top courses</h2>
      <a href="{prefix}course-aml-kyc">AML &amp; KYC</a>
      <a href="{prefix}course-servicenow">ServiceNow</a>
      <a href="{prefix}course-stom">STOM</a>
      <a href="{prefix}course-data-science-ai">Data Science &amp; AI</a>
      <a href="{prefix}course-full-stack-python">Full Stack Python</a>
      <a href="{prefix}courses">All courses</a>
    </nav>
    <nav class="foot-col">
      <h2>AI tools</h2>
      <a href="{prefix}socrates">AI Interview Coach</a>
      <a href="{prefix}resume-evaluator">Resume Evaluator</a>
      <a href="{prefix}skill-gap">Skill Gap</a>
      <a href="{prefix}apply">Apply Assistant</a>
    </nav>
    <nav class="foot-col">
      <h2>Company</h2>
      <a href="{prefix}how-it-works">How it works</a>
      <a href="{prefix}fees">Fees</a>
      <a href="{prefix}jobs">Jobs</a>
      <a href="{prefix}faq">FAQ</a>
      <a href="{prefix}track-record">Track record</a>
      <a href="{prefix}blog">Blog</a>
      <a href="{prefix}terms">Terms</a>
      <a href="{prefix}privacy">Privacy</a>
      <a href="{prefix}refund-policy">Refund Policy</a>
    </nav>
    <div class="foot-col">
      <h2>Contact</h2>
      <a href="tel:+918120694235">+91 81206 94235</a>
      <a href="https://wa.me/918120694235">Chat on WhatsApp</a>
    </div>
  </div>
  <div class="wrap foot-bar">
    <p>© 2026 NaukriSala. All rights reserved.</p>
  </div>
</footer>


<script src="{prefix}script.js"></script>
<script src="{prefix}contact-float.js?v=20261120a"></script>"""
    return nav, foot

def head(title, desc, canon, prefix):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-6780L68WJM"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-6780L68WJM');
</script>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)} | NaukriSala</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="https://naukrisala.in/{canon}">
<meta property="og:title" content="{html.escape(title)} | NaukriSala">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="https://naukrisala.in/{canon}">
<meta property="og:image" content="https://naukrisala.in/assets/brand/ns-logo-blue.png">
<meta property="og:site_name" content="NaukriSala">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{html.escape(title)} | NaukriSala">
<meta name="twitter:description" content="{html.escape(desc)}">
<meta name="twitter:image" content="https://naukrisala.in/assets/brand/ns-logo-blue.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{prefix}styles.css?v=20261122b">
<link rel="stylesheet" href="{prefix}home.css?v=20261120a">
<link rel="stylesheet" href="{prefix}contact-float.css?v=20261120a">
<link rel="icon" type="image/png" href="{prefix}assets/brand/ns-logo-blue.png">
</head>
<body>
"""

# ---------- blog.html ----------
nav, foot = chrome('')
filters = '<button type="button" class="blog-filter active" data-track="all">All topics</button>' + ''.join(
    f'<button type="button" class="blog-filter" data-track="{html.escape(t)}">{html.escape(t)}</button>' for t in TRACKS)
cards = '\n'.join(
    f'      <article class="blog-card" data-track="{html.escape(p["track"])}"><span class="blog-tag">{html.escape(p["track"])}</span><h2><a href="blog/{p["slug"]}">{html.escape(p["title"])}</a></h2><p>{html.escape(p["excerpt"])}</p><span class="blog-read">{p["read"]} min read</span></article>'
    for p in POSTS)
blog_html = head('Blog', 'Practical guides for the careers NaukriSala trains for — compliance, ServiceNow, data, cloud, and the job hunt itself.', 'blog', '') + nav + f"""
<main>
  <section class="section">
    <div class="wrap">
      <div class="sec-head">
        <p class="eyebrow"><span class="dot"></span>Blog</p>
        <h1 class="page-headline">The NaukriSala blog.</h1>
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
# "Keep exploring": same-track guides first, then the track's
# course/jobs pages — see tools/related.py.
for p in POSTS:
    related_html = render_related(related_for_post(p, POSTS), prefix='../',
                                  current='blog/' + p['slug'], indent='      ')
    page = head(p['title'], p['excerpt'], f"blog/{p['slug']}", '../') + nav2 + f"""
<main>
  <section class="section">
    <div class="wrap post-wrap">
      <p class="eyebrow"><span class="dot"></span>{html.escape(p['track'])}</p>
      <h1>{html.escape(p['title'])}</h1>
      <p class="blog-read">{p['read']} min read</p>
      <div class="post-body">{p['body']}</div>
{related_html}
      <div class="post-foot">
        <a class="link-arrow" href="../blog">&larr; Back to the blog</a>
        <a class="btn btn-primary" href="../#demo">Book a free demo <span class="arr">→</span></a>
      </div>
    </div>
  </section>
</main>

""" + foot2 + """
</body>
</html>
"""
    open(f"blog/{p['slug']}", 'w', encoding='utf-8').write(page)
print('generated blog.html +', len(POSTS), 'post pages')
