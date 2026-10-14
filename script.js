// === CONFIG: replace with the real WhatsApp number (country code + number, no +/spaces) ===
const WHATSAPP_NUMBER = "919999999999"; // TODO: Abhigyan — put NaukriSala's WhatsApp number here

const COURSES = [
  { name: "AML & KYC Analyst", tag: "Financial crime compliance · any graduate", dur: "45 days", pay: "₹9–28 LPA", flagship: true,  status: "live", statusLabel: "Batch 1 · Live 10 Nov" },
  { name: "ServiceNow Developer", tag: "Best for freshers & IT support", dur: "3 months", pay: "₹7–18 LPA", flagship: false, status: "soon", statusLabel: "Upcoming" },
  { name: "Data Science & AI Engineering", tag: "Python, ML, GenAI, LLMs, MLOps", dur: "4 months", pay: "₹12–45 LPA", flagship: false, status: "soon", statusLabel: "Upcoming" },
  { name: "STOM — Service Transition & Ops", tag: "Best for non-coders & career switchers", dur: "2 months", pay: "₹8–36 LPA", flagship: false, status: "soon", statusLabel: "Upcoming" },
  { name: "Power BI Developer", tag: "BI & analytics · dashboards + DAX", dur: "2 months", pay: "₹6–18 LPA", flagship: false, status: "soon", statusLabel: "Upcoming" },
  { name: "Data Analyst", tag: "Best for freshers & aspiring analysts", dur: "—", pay: "—", flagship: false, status: "soon", statusLabel: "Upcoming" },
  { name: "Workday Consultant", tag: "Best for HR & operations professionals", dur: "—", pay: "—", flagship: false, status: "soon", statusLabel: "Upcoming" },
  { name: "Full Stack Python", tag: "Best for coding aspirants", dur: "—", pay: "—", flagship: false, status: "soon", statusLabel: "Upcoming" },
  { name: "Full Stack Java Developer", tag: "Best for coding aspirants", dur: "—", pay: "—", flagship: false, status: "soon", statusLabel: "Upcoming" },
  { name: "Software Testing (QA)", tag: "Best for detail-oriented freshers", dur: "—", pay: "—", flagship: false, status: "soon", statusLabel: "Upcoming" },
  { name: "Investment Banking Operations", tag: "Any graduate, no coding needed", dur: "45 days", pay: "₹3.5–7 LPA", flagship: false, status: "soon", statusLabel: "Upcoming" },
  { name: "SAP FICO (S/4HANA Finance)", tag: "Best for B.Com, MBA & finance pros", dur: "—", pay: "—", flagship: false, status: "soon", statusLabel: "Upcoming" },
  { name: "Web Development", tag: "Best for creative coders", dur: "—", pay: "—", flagship: false, status: "soon", statusLabel: "Upcoming" },
  { name: ".NET Developer", tag: "Enterprise stack", dur: "—", pay: "—", flagship: false, status: "soon", statusLabel: "Upcoming" },
  { name: "Database & Business Intelligence", tag: "SQL + BI tools", dur: "—", pay: "—", flagship: false, status: "soon", statusLabel: "Upcoming" },
];

function renderCourses() {
  const grid = document.getElementById("courseGrid");
  grid.innerHTML = COURSES.map(c => `
    <div class="course">
      ${c.flagship ? '<span class="course-flag">Flagship</span>' : ''}
      <h3>${c.name}</h3>
      <p class="tag">${c.tag}</p>
      <div class="meta"><span>${c.dur}</span><span>${c.pay}</span></div>
      <p class="status ${c.status}">${c.statusLabel}</p>
    </div>`).join("");
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
  toggle.addEventListener("click", () => links.classList.toggle("open"));
  links.querySelectorAll("a").forEach(a => a.addEventListener("click", () => links.classList.remove("open")));
}

// Demo form -> WhatsApp deep link
function initDemoForm() {
  const waLink = `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent("Hi NaukriSala! I want to book a free demo class.")}`;
  document.getElementById("waFloat").href = waLink;
  document.getElementById("demoForm").addEventListener("submit", e => {
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
  initDemoForm();
});
