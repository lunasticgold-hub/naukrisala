/* NaukriSala Admin — vanilla JS + Supabase JS v2.
   The anon key below is public by design (safe behind RLS: anon gets nothing). */
const SUPABASE_URL = "https://ccibsfsnnyqdazomwrbw.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNjaWJzZnNubnlxZGF6b213cmJ3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTQ4MzM3NzYsImV4cCI6MjExMDQwOTc3Nn0.bvVwkLeM6lIVLRfmjSeQ6qPY3SBo5mvMOVV7H1KAzvg";
const PAGES_TOTAL = 122;
const sb = window.supabase ? window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY) : null;

const $ = (s) => document.querySelector(s);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[c]));

const state = { jobs: [], jobsMeta: {}, posts: [], flags: [], students: [], leads: [], drafts: [] };
const loaded = { jobs: false, posts: false, flags: false, students: false, leads: false, drafts: false };

/* ---------- edit site registry ----------
   mode: text = plain text node | frag = text between prefix/suffix markup |
   self = element's own text (outerHTML anchor) | child-strong = <strong> inside
   the element (outerHTML anchor) | html = innerHTML (keeps <strong>/<a> until
   edited) | segment = one " · "-separated part of a meta line.
   The worker only applies an edit when old_text matches exactly once in the
   file, so every anchor below was verified against the live files. */
const EDIT_REGISTRY = {
  "index.html": [
    { label: "Hero eyebrow", selector: ".hero-eyebrow", mode: "text" },
    { label: "Hero headline — first line", selector: ".hero-copy h1", mode: "frag", part: "firstText", prefix: "<h1>", suffix: "<br>" },
    { label: "Hero headline — second line", selector: ".hero-copy h1 em", mode: "frag", part: "self", prefix: "<em>", suffix: "</em></h1>" },
    { label: "Hero subtext", selector: ".hero-copy .lede", mode: "html", strongs: ["100% online", "₹15,000"] },
    { label: "Students placed", selector: ".proof-grid .pstat:nth-child(1)", mode: "child-strong" },
    { label: "Average package", selector: ".proof-grid .pstat:nth-child(2)", mode: "child-strong" },
    { label: "Highest package", selector: ".proof-grid .pstat:nth-child(3)", mode: "child-strong" },
    { label: "AI tools", selector: ".proof-grid .pstat:nth-child(4)", mode: "child-strong" },
    { label: "Live class", selector: ".proof-grid .pstat:nth-child(5)", mode: "child-strong" }
  ],
  "fees.html": [
    { label: "Headline — first line", selector: "h1.page-headline", mode: "frag", part: "firstText", prefix: "<h1 class=\"page-headline\">", suffix: " <em>" },
    { label: "Headline — second line", selector: "h1.page-headline em", mode: "frag", part: "self", prefix: "<em>", suffix: "</em></h1>" },
    { label: "Step 1 amount", selector: ".feeflow div.ff-step:nth-of-type(1) .ff-amt", mode: "self" },
    { label: "Step 1 description", selector: ".feeflow div.ff-step:nth-of-type(1) p:not(.ff-amt)", mode: "text" },
    { label: "Step 3 description (after placement)", selector: ".feeflow div.ff-step:nth-of-type(3) p:not(.ff-amt)", mode: "text" },
    { label: "Table — onboarding fee", selector: ".fee-table div.ft-row:nth-of-type(2)", mode: "child-strong" },
    { label: "Table — after offer", selector: ".fee-table div.ft-row:nth-of-type(4)", mode: "child-strong" },
    { label: "Table — if never placed", selector: ".fee-table div.ft-row:nth-of-type(5)", mode: "child-strong" }
  ],
  "course-aml-kyc.html": [
    { label: "Short description", selector: "h1.page-headline + .lede-sm", mode: "self" },
    { label: "Duration", selector: ".course-hero-meta", mode: "segment", index: 0 },
    { label: "Placement range", selector: ".course-hero-meta", mode: "segment", index: 2 }
  ],
  "course-servicenow.html": [
    { label: "Short description", selector: "h1.page-headline + .lede-sm", mode: "self" },
    { label: "Duration", selector: ".course-hero-meta", mode: "segment", index: 0 },
    { label: "Placement range", selector: ".course-hero-meta", mode: "segment", index: 2 }
  ],
  "course-data-science-ai.html": [
    { label: "Short description", selector: "h1.page-headline + .lede-sm", mode: "self" },
    { label: "Duration", selector: ".course-hero-meta", mode: "segment", index: 0 },
    { label: "Placement range", selector: ".course-hero-meta", mode: "segment", index: 2 }
  ],
  "course-stom.html": [
    { label: "Short description", selector: "h1.page-headline + .lede-sm", mode: "self" },
    { label: "Duration", selector: ".course-hero-meta", mode: "segment", index: 0 },
    { label: "Placement range", selector: ".course-hero-meta", mode: "segment", index: 2 }
  ],
  "course-full-stack-python.html": [
    { label: "Short description", selector: "h1.page-headline + .lede-sm", mode: "self" }
  ],
  "track-record.html": [
    { label: "Students placed", selector: ".proof-grid .pstat:nth-child(1)", mode: "child-strong" },
    { label: "Enrolments", selector: ".proof-grid .pstat:nth-child(2)", mode: "child-strong" },
    { label: "Hiring partners", selector: ".proof-grid .pstat:nth-child(3)", mode: "child-strong" },
    { label: "Industry trainers", selector: ".proof-grid .pstat:nth-child(4)", mode: "child-strong" },
    { label: "AI tools", selector: ".proof-grid .pstat:nth-child(5)", mode: "child-strong" },
    { label: "Average package", selector: ".proof-grid .pstat:nth-child(6)", mode: "child-strong" },
    { label: "Median package", selector: ".proof-grid .pstat:nth-child(7)", mode: "child-strong" },
    { label: "Placement rate", selector: ".proof-grid .pstat:nth-child(8)", mode: "child-strong" }
  ],
  "faq.html": [
    { label: "FAQ 1 — How does pay from your salary work?", selector: ".faq-item:nth-child(1) .faq-a p", mode: "html", warnLink: true },
    { label: "FAQ 2 — What if I'm not placed?", selector: ".faq-item:nth-child(2) .faq-a p", mode: "html" },
    { label: "FAQ 3 — Is NaukriSala fully online?", selector: ".faq-item:nth-child(3) .faq-a p", mode: "html", warnLink: true },
    { label: "FAQ 4 — Do I need a coding or IT background?", selector: ".faq-item:nth-child(4) .faq-a p", mode: "html" },
    { label: "FAQ 5 — Are classes live or recorded?", selector: ".faq-item:nth-child(5) .faq-a p", mode: "html" },
    { label: "FAQ 6 — When do demo classes start?", selector: ".faq-item:nth-child(6) .faq-a p", mode: "html", warnLink: true },
    { label: "FAQ 7 — Is the ₹15,000 refundable?", selector: ".faq-item:nth-child(7) .faq-a p", mode: "html" },
    { label: "FAQ 8 — How long is the programme?", selector: ".faq-item:nth-child(8) .faq-a p", mode: "html" },
    { label: "FAQ 9 — How long is each class?", selector: ".faq-item:nth-child(9) .faq-a p", mode: "html" },
    { label: "FAQ 10 — What if I miss a class?", selector: ".faq-item:nth-child(10) .faq-a p", mode: "html" },
    { label: "FAQ 11 — Will you arrange interviews for me?", selector: ".faq-item:nth-child(11) .faq-a p", mode: "html" },
    { label: "FAQ 12 — Will you make my resume and profiles?", selector: ".faq-item:nth-child(12) .faq-a p", mode: "html" },
    { label: "FAQ 13 — What package can I expect?", selector: ".faq-item:nth-child(13) .faq-a p", mode: "html" },
    { label: "FAQ 14 — What is the placement rate?", selector: ".faq-item:nth-child(14) .faq-a p", mode: "html" },
    { label: "FAQ 15 — What do I need to join?", selector: ".faq-item:nth-child(15) .faq-a p", mode: "html" }
  ],
  "how-it-works.html": [
    { label: "Step 1 — Free demo", selector: ".steps .step:nth-child(1) p", mode: "html", strongs: ["29 Dec", "6 Jan"] },
    { label: "Step 2 — Enroll", selector: ".steps .step:nth-child(2) p", mode: "html" },
    { label: "Step 3 — Learn live", selector: ".steps .step:nth-child(3) p", mode: "html" },
    { label: "Step 4 — Build", selector: ".steps .step:nth-child(4) p", mode: "html" },
    { label: "Step 5 — Get placed", selector: ".steps .step:nth-child(5) p", mode: "html" },
    { label: "Step 6 — Pay from salary", selector: ".steps .step:nth-child(6) p", mode: "html" }
  ]
};

/* ---------- auth ---------- */
async function init() {
  if (!sb) {
    $("#loginErr").hidden = false;
    $("#loginErr").textContent = "Could not load the sign-in service. Check your connection and reload.";
    return;
  }
  const { data: { session } } = await sb.auth.getSession();
  const hash = window.location.hash || "";
  // Invite landing (brand-new account, no password yet): the user must set
  // a password now or they cannot log back in later.
  if (hash.includes("type=invite")) {
    $("#setPassBox").hidden = false;
    return;
  }
  // Recovery landing (existing account): the link already signed the user
  // in, so go straight to the app — do NOT trap an authenticated user on
  // the login view. The set-password form is only needed when there is no
  // session yet; password changes inside the app use the Password button.
  if (hash.includes("access_token")) {
    if (session) {
      history.replaceState(null, "", window.location.pathname);
      showApp(session.user);
      return;
    }
    $("#setPassBox").hidden = false;
    return;
  }
  if (session) {
    history.replaceState(null, "", window.location.pathname);
    showApp(session.user);
  }
}

function showApp(user) {
  $("#view-login").hidden = true;
  $("#view-app").hidden = false;
  $("#headUser").textContent = user.email || "";
  loadOverview();
}

$("#loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const err = $("#loginErr");
  err.hidden = true;
  const { data, error } = await sb.auth.signInWithPassword({
    email: $("#loginEmail").value.trim(),
    password: $("#loginPass").value,
  });
  if (error) { err.hidden = false; err.textContent = error.message; return; }
  showApp(data.user);
});

$("#setPassForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const err = $("#setPassErr");
  err.hidden = true;
  const p1 = $("#setPass1").value, p2 = $("#setPass2").value;
  if (p1 !== p2) { err.hidden = false; err.textContent = "Passwords do not match."; return; }
  const { data, error } = await sb.auth.updateUser({ password: p1 });
  if (error) { err.hidden = false; err.textContent = error.message; return; }
  history.replaceState(null, "", window.location.pathname);
  showApp(data.user);
});

$("#logoutBtn").addEventListener("click", async () => {
  await sb.auth.signOut();
  window.location.reload();
});

$("#changePassBtn").addEventListener("click", () => {
  $("#passBox").hidden = !$("#passBox").hidden;
});
$("#passForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const p1 = $("#newPass1").value, p2 = $("#newPass2").value;
  const msg = $("#passMsg");
  msg.hidden = true;
  if (p1 !== p2) { msg.hidden = false; msg.textContent = "Passwords do not match."; return; }
  const { error } = await sb.auth.updateUser({ password: p1 });
  msg.hidden = false;
  msg.textContent = error ? error.message : "Password saved.";
  if (!error) { $("#newPass1").value = ""; $("#newPass2").value = ""; }
});

/* ---------- tabs ---------- */
$("#tabs").addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-tab]");
  if (!btn) return;
  document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("active", b === btn));
  document.querySelectorAll(".tabpane").forEach((p) => { p.hidden = true; });
  const pane = $("#tab-" + btn.dataset.tab);
  pane.hidden = false;
  if (btn.dataset.tab === "jobs") { loadJobs(); loadFlags(); }
  if (btn.dataset.tab === "blog") { loadPosts(); loadDrafts(); }
  if (btn.dataset.tab === "editsite") { loadEditSite(); loadEditStatus(); }
  if (btn.dataset.tab === "students") loadStudents();
  if (btn.dataset.tab === "leads") loadLeads();
});

/* ---------- overview ---------- */
async function loadOverview() {
  const jobsP = loadJobsData();
  const postsP = loadPostsData();
  const [students, leads, drafts] = await Promise.all([
    sb.from("ns_students").select("id", { count: "exact", head: true }),
    sb.from("ns_leads").select("id", { count: "exact", head: true }),
    sb.from("ns_blog_drafts").select("id", { count: "exact", head: true }).eq("status", "pending"),
  ]);
  const jobs = await jobsP;
  const posts = await postsP;
  const aml = jobs.filter((j) => j.course === "aml-kyc").length;
  const cards = [
    ["Live jobs", jobs.length.toLocaleString("en-IN")],
    ["AML & KYC jobs", aml.toLocaleString("en-IN")],
    ["Blog posts", posts.length],
    ["Site pages", PAGES_TOTAL],
    ["Students", students.count ?? 0],
    ["Leads", leads.count ?? 0],
    ["Pending drafts", drafts.count ?? 0],
  ];
  $("#statCards").innerHTML = cards.map(([l, v]) =>
    `<div class="stat"><b>${esc(v)}</b><span>${esc(l)}</span></div>`).join("");
  const f = state.jobsMeta.fetched_at;
  $("#refreshNote").textContent = f
    ? `Board data as of ${f} (nightly refresh). Job hides apply after tonight's refresh.`
    : "";
}

async function loadJobsData() {
  if (state.jobs.length) return state.jobs;
  const res = await fetch("jobs.json");
  const d = await res.json();
  state.jobs = d.jobs || [];
  state.jobsMeta = { fetched_at: d.fetched_at, total: d.total };
  return state.jobs;
}

function loadPostsData() {
  if (state.posts.length) return Promise.resolve(state.posts);
  return new Promise((resolve) => {
    const s = document.createElement("script");
    s.src = "posts.js?cb=" + Date.now();
    s.onload = () => {
      state.posts = (typeof NS_POSTS !== "undefined") ? NS_POSTS : [];
      resolve(state.posts);
    };
    s.onerror = () => resolve([]);
    document.head.appendChild(s);
  });
}

/* ---------- jobs ---------- */
async function loadJobs() {
  await loadJobsData();
  if (!loaded.jobs) {
    const courses = [...new Map(state.jobs.map((j) => [j.course, j.course_label || j.course])).entries()];
    $("#jobCourse").innerHTML = '<option value="">All courses</option>' +
      courses.map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join("");
    loaded.jobs = true;
  }
  renderJobs();
}

function renderJobs() {
  const q = ($("#jobSearch").value || "").toLowerCase();
  const c = $("#jobCourse").value;
  const flagged = new Set(state.flags.map((f) => f.job_id));
  const rows = state.jobs.filter((j) =>
    (!c || j.course === c) &&
    (!q || (j.title + " " + (j.company || "")).toLowerCase().includes(q)));
  $("#jobCount").textContent = rows.length.toLocaleString("en-IN") + " matching jobs (showing first 50)";
  $("#jobList").innerHTML = rows.slice(0, 50).map((j) => {
    const isFlagged = flagged.has(j.id);
    return `<div class="row"><h3>${esc(j.title)}</h3>
      <p>${esc(j.company || "")} · ${esc(j.location || "")}</p>
      <div class="meta"><span class="pill">${esc(j.course_label || j.course)}</span> ${esc(j.contract || "")}</div>
      <div class="actions">
        <a class="btn btn-ghost btn-sm" href="${esc(j.url || "#")}" target="_blank" rel="noopener">View listing</a>
        ${isFlagged
          ? `<button class="btn btn-ghost btn-sm" disabled>Hidden ✓</button>`
          : `<button class="btn btn-danger btn-sm" data-hide="${esc(j.id)}" type="button">Hide job</button>`}
      </div></div>`;
  }).join("") || '<p class="empty">No jobs match.</p>';
}

$("#jobSearch").addEventListener("input", renderJobs);
$("#jobCourse").addEventListener("change", renderJobs);
$("#jobList").addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-hide]");
  if (!btn) return;
  btn.disabled = true;
  const { error } = await sb.from("ns_job_flags").insert({ job_id: btn.dataset.hide, action: "hide" });
  if (error) { alert("Could not hide: " + error.message); btn.disabled = false; return; }
  await loadFlags();
  renderJobs();
});

async function loadFlags() {
  const { data, error } = await sb.from("ns_job_flags").select("*").order("created_at", { ascending: false });
  if (error) { $("#flagList").innerHTML = '<p class="empty">Could not load hidden jobs.</p>'; return; }
  state.flags = data || [];
  loaded.flags = true;
  $("#flagCount").textContent = `(${state.flags.length})`;
  $("#flagList").innerHTML = state.flags.map((f) => {
    const job = state.jobs.find((j) => j.id === f.job_id);
    return `<div class="row"><h3>${job ? esc(job.title) : esc(f.job_id)}</h3>
      <p>${job ? esc((job.company || "") + " · " + (job.location || "")) : "No longer on the board"}</p>
      <div class="actions"><button class="btn btn-ghost btn-sm" data-unflag="${esc(f.job_id)}" type="button">Un-hide</button></div></div>`;
  }).join("") || '<p class="empty">No hidden jobs.</p>';
}

$("#flagList").addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-unflag]");
  if (!btn) return;
  btn.disabled = true;
  const { error } = await sb.from("ns_job_flags").delete().eq("job_id", btn.dataset.unflag);
  if (error) { alert("Could not un-hide: " + error.message); btn.disabled = false; return; }
  await loadFlags();
  renderJobs();
});

/* ---------- blog ---------- */
async function loadPosts() {
  await loadPostsData();
  renderBlog();
}

function renderBlog() {
  const q = ($("#blogSearch").value || "").toLowerCase();
  const rows = state.posts.filter((p) => !q || (p.title + " " + (p.track || "")).toLowerCase().includes(q));
  $("#blogCount").textContent = rows.length + " live posts";
  $("#blogList").innerHTML = rows.slice(0, 50).map((p) =>
    `<div class="row"><h3>${esc(p.title)}</h3>
      <p>${esc(p.excerpt || "")}</p>
      <div class="meta"><span class="pill">${esc(p.track || "")}</span> /blog/${esc(p.slug)}</div></div>`
  ).join("") || '<p class="empty">No posts match.</p>';
}

$("#blogSearch").addEventListener("input", renderBlog);

function slugify(t) {
  return t.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 80);
}
$("#dTitle").addEventListener("input", () => {
  if (!$("#dSlug").dataset.touched) $("#dSlug").value = slugify($("#dTitle").value);
});
$("#dSlug").addEventListener("input", () => { $("#dSlug").dataset.touched = "1"; });

$("#draftForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msg = $("#draftMsg");
  msg.hidden = true;
  const { error } = await sb.from("ns_blog_drafts").insert({
    title: $("#dTitle").value.trim(),
    slug: $("#dSlug").value.trim(),
    track: $("#dTrack").value,
    excerpt: $("#dExcerpt").value.trim(),
    body: $("#dBody").value.trim(),
    status: "pending",
  });
  if (error) { msg.hidden = false; msg.textContent = "Could not save: " + error.message; return; }
  msg.hidden = false;
  msg.textContent = "Draft saved. It is not live until published.";
  e.target.reset();
  $("#dSlug").dataset.touched = "";
  loadDrafts();
});

async function loadDrafts() {
  const { data, error } = await sb.from("ns_blog_drafts").select("*").order("created_at", { ascending: false });
  if (error) { $("#draftList").innerHTML = '<p class="empty">Could not load drafts.</p>'; return; }
  state.drafts = data || [];
  loaded.drafts = true;
  $("#draftCount").textContent = `(${state.drafts.length})`;
  const PILL = { pending: "amber", approved: "", published: "green", failed: "red" };
  $("#draftList").innerHTML = state.drafts.map((d) =>
    `<div class="row"><h3>${esc(d.title)}</h3>
      <p>${esc(d.excerpt || "")}</p>
      <div class="meta"><span class="pill ${PILL[d.status] || ""}">${esc(d.status)}</span> ${esc(d.track || "")} · /blog/${esc(d.slug)}</div>
      ${d.status === "failed" && d.error ? `<p class="err">${esc(d.error)}</p>` : ""}
      <div class="actions">
        ${d.status === "pending" ? `<button class="btn btn-primary btn-sm" data-publish-draft="${esc(d.id)}" type="button">Publish</button>` : ""}
        ${d.status === "approved" ? `<span class="muted">Publishing soon — goes live within a few minutes.</span>` : ""}
        <button class="btn btn-ghost btn-sm" data-del-draft="${esc(d.id)}" type="button">Delete draft</button>
      </div></div>`
  ).join("") || '<p class="empty">No pending drafts.</p>';
}

$("#draftList").addEventListener("click", async (e) => {
  const pubBtn = e.target.closest("[data-publish-draft]");
  if (pubBtn) {
    pubBtn.disabled = true;
    const { error } = await sb.from("ns_blog_drafts").update({ status: "approved" }).eq("id", pubBtn.dataset.publishDraft);
    if (error) { alert("Could not publish: " + error.message); pubBtn.disabled = false; return; }
    loadDrafts();
    return;
  }
  const btn = e.target.closest("[data-del-draft]");
  if (!btn || !confirm("Delete this draft?")) return;
  await sb.from("ns_blog_drafts").delete().eq("id", btn.dataset.delDraft);
  loadDrafts();
});

/* ---------- edit site ---------- */
let editDoc = null;      // parsed live page
let editRaw = "";        // raw live page text (for the uniqueness pre-check)
let editPage = "index.html";

function decodeEntities(s) {
  return s.replace(/&amp;/g, "&").replace(/&rsquo;/g, "’").replace(/&lsquo;/g, "‘")
    .replace(/&ldquo;/g, "“").replace(/&rdquo;/g, "”").replace(/&quot;/g, "\"")
    .replace(/&mdash;/g, "—").replace(/&ndash;/g, "–").replace(/&middot;/g, "·")
    .replace(/&nbsp;/g, " ").replace(/&#8217;/g, "’").replace(/&#8220;/g, "“")
    .replace(/&#8221;/g, "”").replace(/&#8212;/g, "—").replace(/&#183;/g, "·");
}
function countIn(hay, needle) {
  if (!needle) return 0;
  let n = 0, i = 0;
  while ((i = hay.indexOf(needle, i)) !== -1) { n++; i += needle.length; }
  return n;
}
function anchorCount(oldText) {
  const raw = countIn(editRaw, oldText);
  if (raw === 1) return 1;
  return countIn(decodeEntities(editRaw), decodeEntities(oldText));
}

function fieldValue(el, f) {
  if (f.mode === "frag") {
    if (f.part === "firstText") return (el.firstChild ? el.firstChild.textContent : "").trim();
    return el.textContent.trim();
  }
  if (f.mode === "child-strong") return el.querySelector("strong").textContent.trim();
  if (f.mode === "segment") return el.textContent.trim().split("·").map((s) => s.trim())[f.index];
  return el.textContent.trim();
}
function fieldOldText(el, f) {
  const v = fieldValue(el, f);
  if (f.mode === "frag") return f.prefix + v + f.suffix;
  if (f.mode === "self" || f.mode === "child-strong") return el.outerHTML;
  if (f.mode === "html") return el.innerHTML;
  if (f.mode === "segment") {
    const segs = el.textContent.trim().split("·").map((s) => s.trim());
    return segs[f.index + 1] !== undefined ? segs[f.index] + " · " + segs[f.index + 1] : segs[f.index];
  }
  return v;
}
function fieldNewText(el, f, input) {
  const v = input.trim();
  if (f.mode === "frag") return f.prefix + v + f.suffix;
  if (f.mode === "self") return el.outerHTML.replace(el.textContent.trim(), v);
  if (f.mode === "child-strong") return el.outerHTML.replace(el.querySelector("strong").textContent.trim(), v);
  if (f.mode === "html") {
    let out = esc(v);
    for (const phrase of (f.strongs || [])) {
      if (out.includes(phrase)) out = out.replace(phrase, "<strong>" + phrase + "</strong>");
    }
    return out;
  }
  if (f.mode === "segment") {
    const segs = el.textContent.trim().split("·").map((s) => s.trim());
    return segs[f.index + 1] !== undefined ? v + " · " + segs[f.index + 1] : v;
  }
  return v;
}

async function loadEditSite() {
  editPage = $("#editPage").value;
  const box = $("#editFields");
  box.innerHTML = '<p class="muted">Loading the live page…</p>';
  try {
    const res = await fetch(editPage + "?cb=" + Date.now());
    editRaw = await res.text();
    editDoc = new DOMParser().parseFromString(editRaw, "text/html");
  } catch (err) {
    box.innerHTML = '<p class="err">Could not load the live page. Check your connection and reopen this tab.</p>';
    return;
  }
  const fields = EDIT_REGISTRY[editPage] || [];
  box.innerHTML = fields.map((f, i) => {
    const el = editDoc.querySelector(f.selector);
    if (!el) return `<div class="row"><h3>${esc(f.label)}</h3><p class="err">This text was not found on the live page — the page may have changed.</p></div>`;
    const val = fieldValue(el, f);
    const oldText = fieldOldText(el, f);
    const n = anchorCount(oldText);
    const isLong = val.length > 80;
    return `<div class="row edit-field"><h3>${esc(f.label)}</h3>
      <p class="cur-val">Now: ${esc(val)}</p>
      ${f.warnLink ? '<p class="warn">This answer contains a link — editing it will remove the link.</p>' : ""}
      ${n !== 1 ? '<p class="warn">This text could not be matched exactly on the live page — saving may fail at publish time.</p>' : ""}
      ${isLong
        ? `<textarea rows="3" data-field-input="${i}">${esc(val)}</textarea>`
        : `<input type="text" data-field-input="${i}" value="${esc(val)}">`}
      <div class="actions"><button class="btn btn-primary btn-sm" data-save-field="${i}" type="button">Save change</button>
      <span class="ok-msg" data-field-msg="${i}" hidden></span></div></div>`;
  }).join("");
}

$("#editPage").addEventListener("change", loadEditSite);

$("#editFields").addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-save-field]");
  if (!btn) return;
  const i = Number(btn.dataset.saveField);
  const f = (EDIT_REGISTRY[editPage] || [])[i];
  if (!f) return;
  const el = editDoc.querySelector(f.selector);
  if (!el) { alert("This text is no longer on the live page. Reload the tab and try again."); return; }
  const input = document.querySelector(`[data-field-input="${i}"]`);
  const newVal = input.value.trim();
  const oldVal = fieldValue(el, f);
  const msg = document.querySelector(`[data-field-msg="${i}"]`);
  msg.hidden = true;
  if (!newVal) { msg.hidden = false; msg.textContent = "Nothing to save — the field is empty."; return; }
  if (newVal === oldVal) { msg.hidden = false; msg.textContent = "No change — same as the live text."; return; }
  btn.disabled = true;
  const { error } = await sb.from("ns_site_edits").insert({
    page: editPage,
    label: f.label,
    selector: f.selector,
    old_text: fieldOldText(el, f),
    new_text: fieldNewText(el, f, newVal),
    status: "pending",
  });
  btn.disabled = false;
  msg.hidden = false;
  if (error) { msg.textContent = "Could not save: " + error.message; return; }
  msg.textContent = "Saved — goes live within a few minutes.";
  loadEditStatus();
});

async function loadEditStatus() {
  const { data, error } = await sb.from("ns_site_edits").select("*").order("created_at", { ascending: false }).limit(20);
  if (error) { $("#editList").innerHTML = '<p class="empty">Could not load recent edits.</p>'; return; }
  const rows = data || [];
  $("#editCount").textContent = `(${rows.length})`;
  const PILL = { pending: "amber", applied: "green", failed: "red" };
  $("#editList").innerHTML = rows.map((r) =>
    `<div class="row"><h3>${esc(r.label)}</h3>
      <p>${esc(r.page)}</p>
      <div class="meta"><span class="pill ${PILL[r.status] || ""}">${esc(r.status)}</span>
      ${r.applied_at ? " · live " + esc(new Date(r.applied_at).toLocaleString("en-IN")) : ""}
      ${r.status === "pending" ? " · publishing soon" : ""}</div>
      ${r.status === "failed" && r.error ? `<p class="err">${esc(r.error)}</p>` : ""}</div>`
  ).join("") || '<p class="empty">No edits yet — save your first change above.</p>';
}

/* ---------- students ---------- */

/* ---------- students ---------- */
async function loadStudents() {
  const { data, error } = await sb.from("ns_students").select("*").order("created_at", { ascending: false }).limit(200);
  if (error) { $("#studentList").innerHTML = '<p class="empty">Could not load students.</p>'; return; }
  state.students = data || [];
  loaded.students = true;
  renderStudents();
}

function renderStudents() {
  const q = ($("#studentSearch").value || "").toLowerCase();
  const rows = state.students.filter((s) =>
    !q || ((s.name || "") + " " + (s.phone || "") + " " + (s.course || "") + " " + (s.batch || "")).toLowerCase().includes(q));
  $("#studentCount").textContent = rows.length + " students";
  $("#studentList").innerHTML = rows.map((s) => {
    const placed = s.placement_status === "placed";
    return `<div class="row"><h3>${esc(s.name)}</h3>
      <p>${esc(s.course || "")} · ${esc(s.batch || "")} · ${esc(s.phone || "")}</p>
      <div class="meta">
        <span class="pill ${placed ? "green" : "amber"}">${esc(s.placement_status || "")}</span>
        Fee: ${esc(s.fee_status || "")} · Success fee: ${esc(s.success_fee_status || "")}
        ${placed && s.placed_company ? ` · ${esc(s.placed_company)}${s.package_lpa ? " · ₹" + esc(s.package_lpa) + " LPA" : ""}` : ""}
      </div>
      <div class="actions">
        <button class="btn btn-ghost btn-sm" data-edit-student="${esc(s.id)}" type="button">Edit</button>
        <button class="btn btn-danger btn-sm" data-del-student="${esc(s.id)}" type="button">Delete</button>
      </div></div>`;
  }).join("") || '<p class="empty">No students yet — add your first one above.</p>';
}

$("#studentSearch").addEventListener("input", renderStudents);

function studentPayload() {
  return {
    name: $("#sName").value.trim(),
    phone: $("#sPhone").value.trim() || null,
    email: $("#sEmail").value.trim() || null,
    course: $("#sCourse").value,
    batch: $("#sBatch").value.trim() || null,
    enrolled_on: $("#sEnrolled").value || null,
    fee_status: $("#sFee").value,
    success_fee_status: $("#sSuccessFee").value,
    placement_status: $("#sPlacement").value,
    placed_company: $("#sCompany").value.trim() || null,
    package_lpa: $("#sPackage").value ? Number($("#sPackage").value) : null,
    notes: $("#sNotes").value.trim() || null,
  };
}

$("#studentForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msg = $("#studentMsg");
  msg.hidden = true;
  const id = $("#sId").value;
  const { error } = id
    ? await sb.from("ns_students").update(studentPayload()).eq("id", id)
    : await sb.from("ns_students").insert(studentPayload());
  if (error) { msg.hidden = false; msg.textContent = "Could not save: " + error.message; return; }
  msg.hidden = false;
  msg.textContent = "Student saved.";
  resetStudentForm();
  loadStudents();
});

function resetStudentForm() {
  $("#studentForm").reset();
  $("#sId").value = "";
  $("#studentFormTitle").textContent = "Add student";
}
$("#studentReset").addEventListener("click", resetStudentForm);

$("#studentList").addEventListener("click", async (e) => {
  const editBtn = e.target.closest("[data-edit-student]");
  const delBtn = e.target.closest("[data-del-student]");
  if (editBtn) {
    const s = state.students.find((x) => x.id === editBtn.dataset.editStudent);
    if (!s) return;
    $("#sId").value = s.id;
    $("#sName").value = s.name || "";
    $("#sPhone").value = s.phone || "";
    $("#sEmail").value = s.email || "";
    $("#sCourse").value = s.course || "AML & KYC Analyst";
    $("#sBatch").value = s.batch || "";
    $("#sEnrolled").value = s.enrolled_on || "";
    $("#sFee").value = s.fee_status || "pending";
    $("#sSuccessFee").value = s.success_fee_status || "pending";
    $("#sPlacement").value = s.placement_status || "in-training";
    $("#sCompany").value = s.placed_company || "";
    $("#sPackage").value = s.package_lpa ?? "";
    $("#sNotes").value = s.notes || "";
    $("#studentFormTitle").textContent = "Edit student";
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  if (delBtn) {
    if (!confirm("Delete this student? This cannot be undone.")) return;
    const { error } = await sb.from("ns_students").delete().eq("id", delBtn.dataset.delStudent);
    if (error) { alert("Could not delete: " + error.message); return; }
    loadStudents();
  }
});

/* ---------- leads ---------- */
async function loadLeads() {
  const { data, error } = await sb.from("ns_leads").select("*").order("created_at", { ascending: false }).limit(200);
  if (error) { $("#leadList").innerHTML = '<p class="empty">Could not load leads.</p>'; return; }
  state.leads = data || [];
  loaded.leads = true;
  renderLeads();
}

const LEAD_PILL = { new: "", contacted: "amber", "demo-booked": "amber", enrolled: "green", lost: "red" };

function renderLeads() {
  const q = ($("#leadSearch").value || "").toLowerCase();
  const st = $("#leadStatusFilter").value;
  const rows = state.leads.filter((l) =>
    (!st || l.status === st) &&
    (!q || ((l.name || "") + " " + (l.phone || "") + " " + (l.course_interest || "")).toLowerCase().includes(q)));
  $("#leadCount").textContent = rows.length + " leads";
  $("#leadList").innerHTML = rows.map((l) =>
    `<div class="row"><h3>${esc(l.name)}</h3>
      <p>${esc(l.course_interest || "")} · ${esc(l.phone || "")} · ${esc(l.email || "")}</p>
      <div class="meta"><span class="pill ${LEAD_PILL[l.status] || ""}">${esc(l.status || "")}</span> via ${esc(l.source || "")}</div>
      <div class="actions">
        <button class="btn btn-ghost btn-sm" data-edit-lead="${esc(l.id)}" type="button">Edit</button>
        <button class="btn btn-danger btn-sm" data-del-lead="${esc(l.id)}" type="button">Delete</button>
      </div></div>`
  ).join("") || '<p class="empty">No leads yet — add your first one above.</p>';
}

$("#leadSearch").addEventListener("input", renderLeads);
$("#leadStatusFilter").addEventListener("change", renderLeads);

function leadPayload() {
  return {
    name: $("#lName").value.trim(),
    phone: $("#lPhone").value.trim() || null,
    email: $("#lEmail").value.trim() || null,
    course_interest: $("#lCourse").value,
    source: $("#lSource").value,
    status: $("#lStatus").value,
    notes: $("#lNotes").value.trim() || null,
  };
}

$("#leadForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msg = $("#leadMsg");
  msg.hidden = true;
  const id = $("#lId").value;
  const { error } = id
    ? await sb.from("ns_leads").update(leadPayload()).eq("id", id)
    : await sb.from("ns_leads").insert(leadPayload());
  if (error) { msg.hidden = false; msg.textContent = "Could not save: " + error.message; return; }
  msg.hidden = false;
  msg.textContent = "Lead saved.";
  resetLeadForm();
  loadLeads();
});

function resetLeadForm() {
  $("#leadForm").reset();
  $("#lId").value = "";
  $("#leadFormTitle").textContent = "Add lead";
}
$("#leadReset").addEventListener("click", resetLeadForm);

$("#leadList").addEventListener("click", async (e) => {
  const editBtn = e.target.closest("[data-edit-lead]");
  const delBtn = e.target.closest("[data-del-lead]");
  if (editBtn) {
    const l = state.leads.find((x) => x.id === editBtn.dataset.editLead);
    if (!l) return;
    $("#lId").value = l.id;
    $("#lName").value = l.name || "";
    $("#lPhone").value = l.phone || "";
    $("#lEmail").value = l.email || "";
    $("#lCourse").value = l.course_interest || "AML & KYC Analyst";
    $("#lSource").value = l.source || "demo form";
    $("#lStatus").value = l.status || "new";
    $("#lNotes").value = l.notes || "";
    $("#leadFormTitle").textContent = "Edit lead";
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  if (delBtn) {
    if (!confirm("Delete this lead? This cannot be undone.")) return;
    const { error } = await sb.from("ns_leads").delete().eq("id", delBtn.dataset.delLead);
    if (error) { alert("Could not delete: " + error.message); return; }
    loadLeads();
  }
});

/* ---------- links ---------- */
const LINKS = [
  ["Content calendar (60-post plan)", "Google Sheet", "https://docs.google.com/spreadsheets/d/1HhZbQz_-6Zk4Ayura7CByiXC93aNw9DBz7lN5J_GDWk"],
  ["SEO tracker", "Google Sheet", "https://docs.google.com/spreadsheets/d/1a_0aVufzUa50ionxYshEoKNDGgKYV-u5GXwyWYlmsdI"],
  ["Search Console", "naukrisala.in property", "https://search.google.com/search-console"],
  ["Demo form (home page)", "Bookings arrive on WhatsApp", "https://naukrisala.in/#demo"],
  ["Canva brand kit", "Logo, colours, fonts", "https://www.canva.com/brand/kAHZarNI84M"],
  ["Live site", "naukrisala.in", "https://naukrisala.in"],
  ["Jobs board", "naukrisala.in/jobs", "https://naukrisala.in/jobs"],
];
$("#linkList").innerHTML = LINKS.map(([t, s, u]) =>
  `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(t)}<span>${esc(s)} ↗</span></a>`).join("");

init();
