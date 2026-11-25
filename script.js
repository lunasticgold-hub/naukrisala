// === CONFIG: replace with the real WhatsApp number (country code + number, no +/spaces) ===
const WHATSAPP_NUMBER = "918120694235"; // NaukriSala demo bookings (confirmed by Abhigyan 2026-10-14)

const COURSES = [
  { name: "AML & KYC Analyst", tag: "Financial crime compliance · any graduate", dur: "45 days", pay: "TBA", flagship: true,  status: "Batch 9 · Begins 10 Jan", img: "assets/courses/aml-kyc.jpg" },
  { name: "ServiceNow Developer", tag: "Best for freshers & IT support", dur: "3 months", pay: "TBA", flagship: false, status: "Upcoming", img: "assets/courses/servicenow.jpg" },
  { name: "Data Science & AI Engineering", tag: "Python, ML, GenAI, LLMs, MLOps", dur: "4 months", pay: "TBA", flagship: false, status: "Upcoming", img: "assets/courses/data-science-ai.jpg" },
  { name: "STOM — Service Transition & Ops", tag: "Best for non-coders & career switchers", dur: "2 months", pay: "TBA", flagship: false, status: "Upcoming", img: "assets/courses/stom.jpg" },
  { name: "Power BI Developer", tag: "BI & analytics · dashboards + DAX", dur: "2 months", pay: "TBA", flagship: false, status: "Upcoming", img: "assets/courses/power-bi.jpg" },
  { name: "Data Analyst", tag: "Best for freshers & aspiring analysts", dur: "TBA", pay: "TBA", flagship: false, status: "Upcoming", img: "assets/courses/data-analyst.jpg" },
  { name: "Workday Consultant", tag: "Best for HR & operations professionals", dur: "TBA", pay: "TBA", flagship: false, status: "Upcoming", img: "assets/courses/workday.jpg" },
  { name: "Full Stack Python", tag: "Best for coding aspirants", dur: "TBA", pay: "TBA", flagship: false, status: "Upcoming", img: "assets/courses/python-fullstack.jpg" },
  { name: "Full Stack Java Developer", tag: "Best for coding aspirants", dur: "TBA", pay: "TBA", flagship: false, status: "Upcoming", img: "assets/courses/java-fullstack.jpg" },
  { name: "Software Testing (QA)", tag: "Best for detail-oriented freshers", dur: "TBA", pay: "TBA", flagship: false, status: "Upcoming", img: "assets/courses/qa-testing.jpg" },
  { name: "Investment Banking Operations", tag: "Any graduate, no coding needed", dur: "45 days", pay: "TBA", flagship: false, status: "Upcoming", img: "assets/courses/ib-operations.jpg" },
  { name: "SAP FICO (S/4HANA Finance)", tag: "Best for B.Com, MBA & finance pros", dur: "TBA", pay: "TBA", flagship: false, status: "Upcoming", img: "assets/courses/sap-fico.jpg" },
  { name: "Web Development", tag: "Best for creative coders", dur: "TBA", pay: "TBA", flagship: false, status: "Upcoming", img: "assets/courses/web-dev.jpg" },
  { name: ".NET Developer", tag: "Enterprise stack", dur: "TBA", pay: "TBA", flagship: false, status: "Upcoming", img: "assets/courses/dotnet.jpg" },
  { name: "Database & Business Intelligence", tag: "SQL + BI tools", dur: "TBA", pay: "TBA", flagship: false, status: "Upcoming", img: "assets/courses/dbi.jpg" },
];

/* Per-track live-openings counts, counted from jobs.json on 2026-11-25.
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
  "aml-kyc": "course-aml-kyc",
  "servicenow": "course-servicenow",
  "stom": "course-stom",
  "data-science-ai": "course-data-science-ai",
  "python-fullstack": "course-full-stack-python"
};
// Only these two course pages have a syllabus (module/topic list) to link to.
const COURSE_SYLLABUS = {
  "aml-kyc": "course-aml-kyc#syllabus",
  "data-science-ai": "course-data-science-ai#syllabus"
};

// Pay fees buttons pass the course invisibly via sessionStorage, so the
// checkout URL stays a clean /checkout/ (no ?course= in the address bar).
// The checkout page reads it and falls back to ?course= for old links.
document.addEventListener("click", function (e) {
  var a = e.target.closest("a[data-course]");
  if (!a) return;
  try { sessionStorage.setItem("ns_course", a.getAttribute("data-course")); } catch (err) { /* private mode */ }
});
const COURSE_OPENINGS = {
  "aml-kyc": 1136, "servicenow": 194, "data-science-ai": 419, "stom": 111,
  "power-bi": 144, "data-analyst": 231, "workday": 197, "python-fullstack": 379,
  "java-fullstack": 636, "qa-testing": 433, "ib-operations": 143,
  "sap-fico": 132, "web-dev": 218, "dotnet": 218, "dbi": 354
};

function renderCourses() {
  const grid = document.getElementById("courseGrid");
  if (!grid) return;
  const domainOf = {};
  COURSE_DOMAINS.forEach(d => d.courses.forEach(n => { domainOf[n] = d.name; }));
  grid.innerHTML = COURSES.map(c => {
    const slug = COURSE_SLUGS[c.name] || "";
    const openings = COURSE_OPENINGS[slug];
    const hasDur = c.dur && c.dur !== "TBA";
    const batch = c.flagship ? "Batch Starts on 10 Jan 2027" : "Enrolments open";
    return `
    <div class="course${c.flagship ? " flagship" : ""} reveal">
      <a class="course-link" href="${COURSE_PAGE[slug] || "/#demo"}" aria-label="View ${c.name} programme"></a>
      <div class="course-photo">
        <img src="${c.img}" alt="${c.name} — NaukriSala" loading="lazy">
        <span class="course-status">${c.status}</span>
        ${c.flagship ? '<span class="course-flag">Flagship</span>' : ''}
      </div>
      <div class="course-body">
        <span class="course-badge"><img src="assets/brand/ns-logo-blue.png" alt="NaukriSala"></span>
        <p class="course-provider">${domainOf[c.name] || "NaukriSala"}</p>
        <h3>${c.name}</h3>
        <div class="c-meta">
          ${hasDur ? `<span class="c-dur"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>${c.dur}</span>` : ''}
          <span class="c-mode"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="2" y="4" width="20" height="13" rx="2"/><path d="M8 21h8M12 17v4"/></svg>Online</span>
        </div>
        <p class="c-batch">${batch}</p>
        ${openings ? `<p class="c-open-line"><span class="c-open" data-openings="${slug}"><b>${openings.toLocaleString('en-IN')}</b> live openings</span></p>` : ''}
        <div class="course-actions">
          <a class="btn btn-outline" href="${COURSE_PAGE[slug] || "/#demo"}">View Program</a>
          ${c.flagship ? '<a class="btn btn-primary" href="checkout/" data-course="' + c.name + '">Pay fees <span class="arr">→</span></a>' : ''}
        </div>
        ${COURSE_SYLLABUS[slug] ? `<a class="btn btn-outline course-syllabus" href="${COURSE_SYLLABUS[slug]}">Syllabus <span class="arr">→</span></a>` : ''}
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
  return COURSE_PAGE[slug] || "courses";
}
function checkoutLink(name) {
  return "checkout/";
}

function initCoursesDropdown() {
  const links = document.getElementById("navLinks");
  if (!links) return;
  const coursesLink = links.querySelector('a[href="courses"]');
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
    '<div class="cd-foot"><a href="courses">View all 15 courses →</a><a href="/#demo">Book a free demo →</a></div></div>';
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
        (name === "AML & KYC Analyst" ? '<a class="btn btn-outline btn-sm cd-pay" href="' + checkoutLink(name) + '" data-course="' + name + '">Pay fees</a>' : '') +
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
    const msg = `Hi NaukriSala! I'm ${name} (${phone}). I want to book a free demo class for: ${course}. Demo classes 2–7 Jan 2027.`;
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
