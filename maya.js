/* Maya — NaukriSala's on-site guide.
   Rule-based: every answer comes from the site's published facts.
   Maya never invents fees, outcomes, eligibility rules, or placement claims.
   When she doesn't know, she points to WhatsApp or a free demo. */
(function () {
  var prefix = window.location.pathname.indexOf('/blog/') !== -1 ? '../' : '';
  var WA = 'https://wa.me/918450049035';
  function L(path) { return prefix + path; }
  function demoLink() { return '<a href="' + L('index.html#demo') + '">Book a free demo</a>'; }

  var KB = [
    { test: function (t) { return /\b(hi|hello|hey|namaste)\b/.test(t); },
      reply: function () { return "Hi, I'm Maya — your NaukriSala guide. Ask me about courses, fees, placement, batches, or the jobs board. Or tap a topic below."; } },
    { test: function (t) { return /who are you|your name|are you (a )?real|are you ai|are you a bot/.test(t); },
      reply: function () { return "I'm Maya, NaukriSala's on-site guide. I answer from the site's published information — if I don't know something, I'll point you to WhatsApp or a free demo instead of guessing."; } },
    { test: function (t) { return /placement|placed|offer letter|pay after|pay from salary/.test(t); },
      reply: function () { return "Placement support continues until you hold an offer letter: resume and LinkedIn overhaul, mock interviews, referrals, and interview scheduling. Joining starts at ₹15,000; the rest is paid only after placement, in installments from your salary. Results depend on your participation, attendance, and interview performance — we don't promise a specific employer, role, or salary. " + demoLink() + " to talk it through."; } },
    { test: function (t) { return /fee|price|cost|15000|15,000|payment|instalment|installment|how much/.test(t); },
      reply: function () { return "Joining starts with a ₹15,000 onboarding fee. Nothing more is due during training — the rest is paid only after placement, in installments from your salary. The exact arrangement for your track is confirmed with you on your demo call, before you pay. Details: <a href=\"" + L('fees.html') + "\">Fees</a>."; } },
    { test: function (t) { return /aml|kyc/.test(t); },
      reply: function () { return "AML &amp; KYC Analyst is the flagship track — 45 days, live online classes. It covers KYC/CDD, transaction monitoring, sanctions screening, and reporting. See the track: <a href=\"" + L('course-aml-kyc.html') + "\">AML &amp; KYC</a>, or " + demoLink() + " to sit in a real class."; } },
    { test: function (t) { return /servicenow/.test(t); },
      reply: function () { return "ServiceNow Developer runs 3 months, live online. It covers ITSM, workflows, and building on the ServiceNow platform. See the track: <a href=\"" + L('course-servicenow.html') + "\">ServiceNow</a>."; } },
    { test: function (t) { return /\bstom\b/.test(t); },
      reply: function () { return "STOM runs 2 months, live online — service transition and operations roles for people who want an IT career without heavy coding. See the track: <a href=\"" + L('course-stom.html') + "\">STOM</a>."; } },
    { test: function (t) { return /data science|machine learning|\bml\b|genai|artificial intelligence/.test(t); },
      reply: function () { return "Data Science &amp; AI Engineering runs 4 months — Python, ML, GenAI/LLMs, and MLOps, live online. See the track: <a href=\"" + L('course-data-science-ai.html') + "\">Data Science &amp; AI</a>."; } },
    { test: function (t) { return /python|full stack/.test(t); },
      reply: function () { return "Full Stack Python covers Python plus frontend and backend development, live online. The full curriculum is covered in the free demo class. See the track: <a href=\"" + L('course-full-stack-python.html') + "\">Full Stack Python</a>."; } },
    { test: function (t) { return /course|track|which course|what should i (learn|study|do)/.test(t); },
      reply: function () { return "Five tracks, all 100% online and live: AML &amp; KYC Analyst (45 days), ServiceNow Developer (3 months), STOM (2 months), Data Science &amp; AI Engineering (4 months), and Full Stack Python. See them all: <a href=\"" + L('courses.html') + "\">Courses</a> — or " + demoLink() + " and we'll help you pick."; } },
    { test: function (t) { return /batch|demo|start|join|enroll|november|nov\b/.test(t); },
      reply: function () { return "Batch 9 starts 10 Nov 2026, and free demo classes run from 3 Nov 2026. " + demoLink() + " — you'll see a real class before you pay anything."; } },
    { test: function (t) { return /apply assistant|resume evaluator|skill gap|interview coach|mock interview|\bai tool/.test(t); },
      reply: function () { return "Four free tools, no sign-up: AI Interview Coach (mock interviews), Resume Evaluator, Skill Gap planner, and Apply Assistant — which drafts tailored resume points and screening answers that you review and submit. Nothing is auto-submitted. Try them: <a href=\"" + L('ai-tools.html') + "\">AI tools</a>."; } },
    { test: function (t) { return /job|board|opening|vacancy|hiring|apply/.test(t); },
      reply: function () { return "The jobs board lists live openings from employer career pages and job boards, refreshed every morning. Apply links go to the employer's own site. See it: <a href=\"" + L('jobs.html') + "\">Jobs board</a>."; } },
    { test: function (t) { return /certificate/.test(t); },
      reply: function () { return "We don't sell certificates. Most academies sell certificates — we sell outcomes: the goal is an offer letter, and placement support continues until you hold one."; } },
    { test: function (t) { return /eligib|degree|qualification|fresher|experience|am i eligible|can i join/.test(t); },
      reply: function () { return "The free demo call covers whether a track fits your background — that's the honest way to check fit. " + demoLink() + " and ask."; } },
    { test: function (t) { return /human|call|contact|whatsapp|phone|talk to|callback/.test(t); },
      reply: function () { return "Want a human? Message us on <a href=\"" + WA + "\">WhatsApp</a> or " + demoLink() + " and we'll call you back."; } },
    { test: function (t) { return /how (does|do) (it|this|naukrisala) work|how it works|process|steps/.test(t); },
      reply: function () { return "1. Book a free demo. 2. Join with ₹15,000. 3. Train in live, 100% online classes. 4. Get placement support until you hold an offer. 5. Pay the rest from your salary after you're placed. Full walkthrough: <a href=\"" + L('how-it-works.html') + "\">How it works</a>."; } }
  ];
  var FALLBACK = "I don't have that answer yet. Message us on <a href=\"" + WA + "\">WhatsApp</a> or " + demoLink() + " — a human will help you there.";

  function answer(text) {
    var t = ' ' + text.toLowerCase().replace(/[^a-z0-9₹, ]/g, ' ') + ' ';
    for (var i = 0; i < KB.length; i++) {
      if (KB[i].test(t)) return KB[i].reply();
    }
    return FALLBACK;
  }

  /* ---- widget DOM ---- */
  var launcher = document.createElement('button');
  launcher.className = 'maya-launcher';
  launcher.setAttribute('aria-label', 'Chat with Maya');
  launcher.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>';
  var panel = document.createElement('div');
  panel.className = 'maya-panel';
  panel.innerHTML =
    '<div class="maya-head"><span class="maya-avatar">M</span><div><b>Maya</b><span>Your NaukriSala guide</span></div>' +
    '<button class="maya-close" aria-label="Close chat">&times;</button></div>' +
    '<div class="maya-msgs"></div>' +
    '<div class="maya-chips">' +
    '<button class="maya-chip">Fees</button><button class="maya-chip">Placement</button>' +
    '<button class="maya-chip">Which course?</button><button class="maya-chip">Batch 9 &amp; demos</button></div>' +
    '<div class="maya-actions">' +
    '<a class="cb" href="' + WA + '?text=' + encodeURIComponent('Hi NaukriSala, please call me back about courses.') + '" target="_blank" rel="noopener">Request a callback</a>' +
    '<a class="wa" href="' + WA + '" target="_blank" rel="noopener">WhatsApp</a></div>' +
    '<form class="maya-form"><input type="text" placeholder="Ask about courses, fees, placement…" aria-label="Ask Maya">' +
    '<button type="submit" aria-label="Send">&rarr;</button></form>';
  document.body.appendChild(launcher);
  document.body.appendChild(panel);
  var msgs = panel.querySelector('.maya-msgs');
  var greeted = false;

  function addMsg(text, who) {
    var d = document.createElement('div');
    d.className = 'maya-msg ' + who;
    if (who === 'bot') d.innerHTML = text; else d.textContent = text;
    msgs.appendChild(d);
    msgs.scrollTop = msgs.scrollHeight;
  }
  function ask(text) {
    addMsg(text, 'user');
    var typing = document.createElement('div');
    typing.className = 'maya-typing';
    typing.textContent = 'Maya is typing…';
    msgs.appendChild(typing);
    msgs.scrollTop = msgs.scrollHeight;
    setTimeout(function () {
      typing.remove();
      addMsg(answer(text), 'bot');
    }, 600);
  }
  function open() {
    panel.classList.add('open');
    if (!greeted) {
      greeted = true;
      addMsg("Hi, I'm Maya — your NaukriSala guide. Ask me about courses, fees, placement, batches, or the jobs board. Or tap a topic below.", 'bot');
    }
  }
  launcher.addEventListener('click', function () { panel.classList.contains('open') ? panel.classList.remove('open') : open(); });
  panel.querySelector('.maya-close').addEventListener('click', function () { panel.classList.remove('open'); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') panel.classList.remove('open'); });
  panel.querySelectorAll('.maya-chip').forEach(function (chip) {
    chip.addEventListener('click', function () { ask(chip.textContent.replace('&', 'and')); });
  });
  panel.querySelector('.maya-form').addEventListener('submit', function (e) {
    e.preventDefault();
    var input = panel.querySelector('.maya-form input');
    var v = input.value.trim();
    if (!v) return;
    input.value = '';
    ask(v);
  });
})();
