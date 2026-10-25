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

/* Per-track live-openings counts, counted from jobs.json on 2026-10-20.
   The homepage wiring refreshes them from jobs.json on every load —
   these values are the static fallback. Keys are jobs.json course slugs. */
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
  "aml-kyc": 567, "servicenow": 145, "data-science-ai": 253, "stom": 75,
  "power-bi": 58, "data-analyst": 147, "workday": 122, "python-fullstack": 202,
  "java-fullstack": 346, "qa-testing": 236, "ib-operations": 91,
  "sap-fico": 88, "web-dev": 96, "dotnet": 122, "dbi": 223
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
  initFaq();
  initNav();
  initReveal();
  initDemoForm();
});
