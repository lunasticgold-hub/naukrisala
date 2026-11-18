// === CONFIG: replace with the real WhatsApp number (country code + number, no +/spaces) ===
const WHATSAPP_NUMBER = "918450049035"; // NaukriSala demo bookings (confirmed by Abhigyan 2026-10-14)

const COURSES = [
  { name: "AML & KYC Analyst", tag: "Financial crime compliance · any graduate", dur: "45 days", pay: "₹9–28 LPA", flagship: true,  status: "Batch 9 · Live 10 Nov" },
  { name: "ServiceNow Developer", tag: "Best for freshers & IT support", dur: "3 months", pay: "₹7–18 LPA", flagship: false, status: "Upcoming" },
  { name: "Data Science & AI Engineering", tag: "Python, ML, GenAI, LLMs, MLOps", dur: "4 months", pay: "₹12–45 LPA", flagship: false, status: "Upcoming" },
  { name: "STOM — Service Transition & Ops", tag: "Best for non-coders & career switchers", dur: "2 months", pay: "₹8–36 LPA", flagship: false, status: "Upcoming" },
  { name: "Power BI Developer", tag: "BI & analytics · dashboards + DAX", dur: "2 months", pay: "₹6–18 LPA", flagship: false, status: "Upcoming" },
  { name: "Data Analyst", tag: "Best for freshers & aspiring analysts", dur: "TBA", pay: "TBA", flagship: false, status: "Upcoming" },
  { name: "Workday Consultant", tag: "Best for HR & operations professionals", dur: "TBA", pay: "TBA", flagship: false, status: "Upcoming" },
  { name: "Full Stack Python", tag: "Best for coding aspirants", dur: "TBA", pay: "TBA", flagship: false, status: "Upcoming" },
  { name: "Full Stack Java Developer", tag: "Best for coding aspirants", dur: "TBA", pay: "TBA", flagship: false, status: "Upcoming" },
  { name: "Software Testing (QA)", tag: "Best for detail-oriented freshers", dur: "TBA", pay: "TBA", flagship: false, status: "Upcoming" },
  { name: "Investment Banking Operations", tag: "Any graduate, no coding needed", dur: "45 days", pay: "₹3.5–7 LPA", flagship: false, status: "Upcoming" },
  { name: "SAP FICO (S/4HANA Finance)", tag: "Best for B.Com, MBA & finance pros", dur: "TBA", pay: "TBA", flagship: false, status: "Upcoming" },
  { name: "Web Development", tag: "Best for creative coders", dur: "TBA", pay: "TBA", flagship: false, status: "Upcoming" },
  { name: ".NET Developer", tag: "Enterprise stack", dur: "TBA", pay: "TBA", flagship: false, status: "Upcoming" },
  { name: "Database & Business Intelligence", tag: "SQL + BI tools", dur: "TBA", pay: "TBA", flagship: false, status: "Upcoming" },
];

/* Per-track live-openings counts, counted from jobs.json on 2026-11-18.
   The homepage, courses page and course pages refresh them from jobs.json
   on every load — these values are the static fallback. Keys are jobs.json course slugs. */
const COURSE_SLUGS = {
  "AML & KYC Analyst": "aml-kyc",
  "ServiceNow Developer": "servicenow",
  "Data Science & AI Engineering": "data-science-ai",
  "STOM — Service Transition & Ops": "stom",
  "Power BI Developer": "power-bi",
  "Data Analyst": "data-analyst",
  "Workday Consultant": "workday",
  "Full Stack Python": "python-fullstack",
  "Full Stack Java Developer": "java-fullstack",
  "Software Testing (QA)": "qa-testing",
  "Investment Banking Operations": "ib-operations",
  "SAP FICO (S/4HANA Finance)": "sap-fico",
  "Web Development": "web-dev",
  ".NET Developer": "dotnet",
  "Database & Business Intelligence": "dbi"
};
const COURSE_PAGE = {
  "aml-kyc": "course-aml-kyc.html",
  "servicenow": "course-servicenow.html",
  "stom": "course-stom.html",
  "data-science-ai": "course-data-science-ai.html",
  "python-fullstack": "course-full-stack-python.html"
};
const COURSE_OPENINGS = {
  "aml-kyc": 1167, "servicenow": 199, "data-science-ai": 404, "stom": 107,
  "power-bi": 138, "data-analyst": 230, "workday": 198, "python-fullstack": 364,
  "java-fullstack": 595, "qa-testing": 414, "ib-operations": 143,
  "sap-fico": 135, "web-dev": 217, "dotnet": 222, "dbi": 335
};
/* Topic chips: taken from the course's own tag line where it lists topics;
   the flagship's chips come from its curriculum topics on this page. */
const COURSE_CHIPS = {
  "aml-kyc": ["KYC & Customer Onboarding", "CDD — Customer Due Diligence", "EDD — Enhanced Due Diligence", "Transaction Monitoring", "Sanctions & Name Screening", "SAR / STR Reporting"]
};
function courseChips(c, slug) {
  if (COURSE_CHIPS[slug]) return COURSE_CHIPS[slug];
  const tag = c.tag || "";
  if (/^(best for|any graduate)/i.test(tag)) return [];
  const parts = tag.split(/[,+·]/).map(s => s.trim()).filter(Boolean);
  if (parts.length < 2) return [];
  return parts.slice(0, 6).map(s => s.charAt(0).toUpperCase() + s.slice(1));
}

function renderCourses() {
  const grid = document.getElementById("courseGrid");
  if (!grid) return;
  grid.innerHTML = COURSES.map(c => {
    const slug = COURSE_SLUGS[c.name] || "";
    const openings = COURSE_OPENINGS[slug];
    const chips = courseChips(c, slug);
    const hasPay = c.pay && c.pay !== "TBA";
    const hasDur = c.dur && c.dur !== "TBA";
    return `
    <div class="course${c.flagship ? " flagship" : ""} reveal">
      ${c.flagship ? '<span class="course-flag">Flagship</span>' : ''}
      <p class="course-tag">${c.status}</p>
      <h3>${c.name}</h3>
      <p class="tag">${c.tag}</p>
      ${chips.length ? `<div class="c-chips">${chips.map(t => `<span class="c-chip">${t}</span>`).join("")}</div>` : ''}
      <div class="c-meta">
        ${openings ? `<span class="c-open" data-openings="${slug}"><b>${openings.toLocaleString('en-IN')}</b> live openings</span>` : ''}
        ${hasDur ? `<span class="c-dur">${c.dur} · Live online</span>` : ''}
      </div>
      ${hasPay ? `<p class="pay">${c.pay}<small>placement range</small></p>` : ''}
      <p class="c-fee">₹15,000 to start — rest after placement, from salary</p>
      <div class="foot">
        <span class="dur">${hasDur ? c.dur : c.status}</span>
        <a class="go" href="${COURSE_PAGE[slug] || "index.html#demo"}">Details →</a>
      </div>
      <a class="btn btn-primary btn-block pay-fees" href="checkout.html?course=${encodeURIComponent(c.name)}">Pay fees <span class="arr">→</span></a>
      <span class="course-bar"></span>
    </div>`;
  }).join("");
  // cursor spotlight
  grid.querySelectorAll(".course").forEach(card => {
    card.addEventListener("pointermove", e => {
      const r = card.getBoundingClientRect();
      card.style.setProperty("--mx", (e.clientX - r.left) + "px");
      card.style.setProperty("--my", (e.clientY - r.top) + "px");
    });
  });
}

/* Courses mega-dropdown: domains on the left, courses on the right.
   Built from COURSES so it stays in sync with the course grid.
   The panel is injected next to the nav "Courses" link, so every page
   that loads script.js gets it with no per-page HTML edits. */
const COURSE_DOMAINS = [
  { name: "Finance & Compliance", courses: ["AML & KYC Analyst", "Investment Banking Operations", "SAP FICO (S/4HANA Finance)"] },
  { name: "Data & AI", courses: ["Data Science & AI Engineering", "Data Analyst", "Power BI Developer", "Database & Business Intelligence"] },
  { name: "Software Development", courses: ["Full Stack Python", "Full Stack Java Developer", "Web Development", ".NET Developer", "Software Testing (QA)"] },
  { name: "Enterprise Apps & Ops", courses: ["ServiceNow Developer", "STOM — Service Transition & Ops", "Workday Consultant"] },
];

function courseMeta(name) {
  const c = COURSES.find(x => x.name === name);
  if (!c) return "";
  const bits = [];
  if (c.dur && c.dur !== "TBA") bits.push(c.dur);
  if (c.pay && c.pay !== "TBA") bits.push(c.pay + " placement range");
  if (bits.length) return bits.join(" · ");
  return c.status || ""; // e.g. "Upcoming batch" for tracks with no published duration/pay yet
}
function coursePageFor(name) {
  const slug = COURSE_SLUGS[name] || "";
  return COURSE_PAGE[slug] || "courses.html";
}
function checkoutLink(name) {
  return "checkout.html?course=" + encodeURIComponent(name);
}

function initCoursesDropdown() {
  const links = document.getElementById("navLinks");
  if (!links) return;
  const coursesLink = links.querySelector('a[href="courses.html"]');
  if (!coursesLink || document.querySelector(".courses-drop")) return;

  const drop = document.createElement("div");
  drop.className = "courses-drop";
  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "courses-toggle";
  toggle.setAttribute("aria-expanded", "false");
  toggle.setAttribute("aria-haspopup", "true");
  toggle.innerHTML = 'Courses <span class="chev">▾</span>';
  const panel = document.createElement("div");
  panel.className = "courses-panel";
  panel.innerHTML =
    '<div class="cd-domains">' +
      COURSE_DOMAINS.map((d, i) =>
        '<button type="button" class="cd-domain' + (i === 0 ? " active" : "") + '" data-i="' + i + '">' + d.name + "</button>"
      ).join("") +
    "</div>" +
    '<div class="cd-main"><h4 class="cd-title"></h4><div class="cd-list"></div>' +
    '<div class="cd-foot"><a href="courses.html">View all 15 courses →</a><a href="index.html#demo">Book a free demo →</a></div></div>';
  drop.appendChild(toggle);
  drop.appendChild(panel);
  coursesLink.replaceWith(drop);

  const title = panel.querySelector(".cd-title");
  const list = panel.querySelector(".cd-list");
  function renderDomain(i) {
    const d = COURSE_DOMAINS[i];
    panel.querySelectorAll(".cd-domain").forEach(b =>
      b.classList.toggle("active", Number(b.dataset.i) === i));
    title.textContent = d.name;
    list.innerHTML = d.courses.map(name => {
      const meta = courseMeta(name);
      return '<div class="cd-course">' +
        '<a class="cd-name" href="' + coursePageFor(name) + '">' + name +
        (meta ? "<span>" + meta + "</span>" : "") + "</a>" +
        '<a class="btn btn-primary btn-sm cd-pay" href="' + checkoutLink(name) + '">Pay fees</a>' +
        "</div>";
    }).join("");
  }
  renderDomain(0);
  panel.querySelectorAll(".cd-domain").forEach(b =>
    b.addEventListener("click", () => renderDomain(Number(b.dataset.i))));

  function close() {
    drop.classList.remove("open");
    toggle.setAttribute("aria-expanded", "false");
  }
  toggle.addEventListener("click", e => {
    e.stopPropagation();
    const willOpen = !drop.classList.contains("open");
    drop.classList.toggle("open", willOpen);
    toggle.setAttribute("aria-expanded", willOpen ? "true" : "false");
  });
  document.addEventListener("click", e => { if (!drop.contains(e.target)) close(); });
  document.addEventListener("keydown", e => { if (e.key === "Escape") close(); });
  panel.querySelectorAll("a").forEach(a => a.addEventListener("click", close));
}

// FAQ accordion
function initFaq() {
  document.querySelectorAll(".faq-item").forEach(item => {
    item.querySelector(".faq-q").addEventListener("click", () => {
      const wasOpen = item.classList.contains("open");
      document.querySelectorAll(".faq-item").forEach(i => i.classList.remove("open"));
      if (!wasOpen) item.classList.add("open");
    });
  });
}

// Mobile nav
function initNav() {
  const toggle = document.getElementById("navToggle");
  const links = document.getElementById("navLinks");
  if (!toggle || !links) return;
  toggle.addEventListener("click", () => links.classList.toggle("open"));
  links.querySelectorAll("a").forEach(a => a.addEventListener("click", () => links.classList.remove("open")));
}

// Scroll reveal
function initReveal() {
  if (!('IntersectionObserver' in window)) { document.querySelectorAll(".reveal").forEach(el => el.classList.add("in")); return; }
  const io = new IntersectionObserver(entries => {
    entries.forEach(en => { if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); } });
  }, { threshold: 0.12 });
  document.querySelectorAll(".reveal").forEach(el => io.observe(el));
}

// Demo form -> WhatsApp deep link
function initDemoForm() {
  const waLink = `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent("Hi NaukriSala! I want to book a free demo class.")}`;
  const waFloat = document.getElementById("waFloat");
  if (waFloat) waFloat.href = waLink;
  const form = document.getElementById("demoForm");
  if (!form) return;
  form.addEventListener("submit", e => {
    e.preventDefault();
    const name = document.getElementById("fName").value.trim();
    const phone = document.getElementById("fPhone").value.trim();
    const course = document.getElementById("fCourse").value;
    const msg = `Hi NaukriSala! I'm ${name} (${phone}). I want to book a free demo class for: ${course}. Demo classes start 3 Nov.`;
    window.open(`https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(msg)}`, "_blank");
  });
}

document.addEventListener("DOMContentLoaded", () => {
  renderCourses();
  initCoursesDropdown();
  initFaq();
  initNav();
  initReveal();
  initDemoForm();
});
