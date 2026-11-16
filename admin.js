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

/* ---------- auth ---------- */
async function init() {
  if (!sb) {
    $("#loginErr").hidden = false;
    $("#loginErr").textContent = "Could not load the sign-in service. Check your connection and reload.";
    return;
  }
  const { data: { session } } = await sb.auth.getSession();
  const hash = window.location.hash || "";
  if (session) {
    history.replaceState(null, "", window.location.pathname);
    showApp(session.user);
  } else {
    if (hash.includes("type=invite") || hash.includes("access_token")) {
      $("#setPassBox").hidden = false;
    }
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
      <div class="meta"><span class="pill">${esc(p.track || "")}</span> /blog/${esc(p.slug)}.html</div></div>`
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
  $("#draftList").innerHTML = state.drafts.map((d) =>
    `<div class="row"><h3>${esc(d.title)}</h3>
      <p>${esc(d.excerpt || "")}</p>
      <div class="meta"><span class="pill amber">${esc(d.status)}</span> /blog/${esc(d.slug)}.html</div>
      <div class="actions"><button class="btn btn-ghost btn-sm" data-del-draft="${esc(d.id)}" type="button">Delete draft</button></div></div>`
  ).join("") || '<p class="empty">No pending drafts.</p>';
}

$("#draftList").addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-del-draft]");
  if (!btn || !confirm("Delete this draft?")) return;
  await sb.from("ns_blog_drafts").delete().eq("id", btn.dataset.delDraft);
  loadDrafts();
});

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
  ["Jobs board", "naukrisala.in/jobs.html", "https://naukrisala.in/jobs.html"],
];
$("#linkList").innerHTML = LINKS.map(([t, s, u]) =>
  `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(t)}<span>${esc(s)} ↗</span></a>`).join("");

init();
