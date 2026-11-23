// NaukriSala — Razorpay Standard Checkout (checkout/).
// Same flow as pay.js (fees.html): form -> create-razorpay-order
// (server sets the price) -> Razorpay modal -> verify-razorpay-payment.
// The course arrives invisibly in sessionStorage from a Pay fees button
// (so the address bar stays a clean /checkout/). An explicit ?course=<name>
// in the URL wins over the stored value, so a shared link always shows
// its own course; if both are missing or not a real course, the visitor
// picks one from the dropdown.
// The amount is never sent from this file; the backend looks it up.
// The Razorpay secret never appears here — only the public key ID,
// which the create-order function returns.
(function () {
  var FUNCTIONS_URL = "https://ccibsfsnnyqdazomwrbw.supabase.co/functions/v1";
  // Public anon key (same value as admin.js / pay.js — safe to expose in the browser).
  var ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNjaWJzZnNubnlxZGF6b213cmJ3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTQ4MzM3NzYsImV4cCI6MjExMDQwOTc3Nn0.bvVwkLeM6lIVLRfmjSeQ6qPY3SBo5mvMOVV7H1KAzvg";
  var PRODUCT = "onboarding";

  // Every real course name (script.js COURSES + the fees-page labels).
  // Anything else in ?course= is ignored and the visitor picks instead.
  var KNOWN_COURSES = [ "AML & KYC Analyst" ];

  var form = document.getElementById("coForm");
  if (!form) return;
  var btn = document.getElementById("coPayBtn");
  var btnLabel = document.getElementById("coPayLabel");
  var msg = document.getElementById("coMsg");
  var result = document.getElementById("coResult");
  var courseFixed = document.getElementById("coCourseFixed");
  var courseField = document.getElementById("coCourseField");
  var courseSel = document.getElementById("coCourseSel");
  var courseNameEl = document.getElementById("coCourseName");
  var busy = false;

  // Course: an explicit ?course= in the URL wins; otherwise the value
  // stored invisibly in sessionStorage by a Pay fees button (so the
  // address bar stays a clean /checkout/). Show it in the order summary
  // and lock it in; otherwise show the course picker.
  var storedCourse = "";
  try { storedCourse = sessionStorage.getItem("ns_course") || ""; } catch (e) { /* private mode */ }
  var params = new URLSearchParams(window.location.search);
  var courseParam = ((params.get("course") || storedCourse) || "").trim();
  if (KNOWN_COURSES.indexOf(courseParam) !== -1) {
    courseFixed.value = courseParam;
    courseNameEl.textContent = courseParam;
    courseField.style.display = "none";
  } else {
    courseField.style.display = "block";
    courseNameEl.textContent = "Choose below";
  }

  function showMsg(text, isError) {
    msg.textContent = text;
    msg.style.display = "block";
    msg.style.color = isError ? "#b42318" : "var(--ink2)";
  }
  function hideMsg() { msg.style.display = "none"; }
  function setBusy(on, label) {
    busy = on;
    btn.disabled = on;
    btnLabel.textContent = label || "Pay ₹15,000 securely";
    btn.style.opacity = on ? ".65" : "1";
    btn.style.cursor = on ? "wait" : "pointer";
  }
  function showResult(data) {
    result.innerHTML =
      "<h3>Payment successful</h3>" +
      "<p>Your onboarding fee is paid and your seat is confirmed. Keep your Payment ID safe — it is your receipt.</p>" +
      "<div class=\"pay-details\">" +
      "<div><span>Payment ID</span><strong>" + esc(data.payment_id) + "</strong></div>" +
      "<div><span>Order ID</span><strong>" + esc(data.order_id) + "</strong></div>" +
      "<div><span>Amount paid</span><strong>₹" + (data.amount / 100).toLocaleString("en-IN") + "</strong></div>" +
      "<div><span>Course</span><strong>" + esc(data.course || "") + "</strong></div>" +
      "</div>" +
      "<p class=\"fine\">If anything looks wrong, message us on <a href=\"https://wa.me/918120694235\">WhatsApp</a> with your Payment ID.</p>";
    result.style.display = "block";
    result.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  async function callFn(name, payload) {
    var res = await fetch(FUNCTIONS_URL + "/" + name, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        apikey: ANON_KEY,
        Authorization: "Bearer " + ANON_KEY,
      },
      body: JSON.stringify(payload),
    });
    var data = null;
    try { data = await res.json(); } catch (e) { /* non-JSON error body */ }
    if (!res.ok) {
      var err = new Error((data && data.error) || "request_failed");
      err.status = res.status;
      throw err;
    }
    return data;
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    if (busy) return; // no duplicate submissions
    hideMsg();
    result.style.display = "none";

    var name = document.getElementById("coName").value.trim();
    var email = document.getElementById("coEmail").value.trim();
    var phone = document.getElementById("coPhone").value.trim();
    var course = courseFixed.value || courseSel.value;
    if (name.length < 2) return showMsg("Please enter your full name.", true);
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return showMsg("Please enter a valid email address.", true);
    if (phone.replace(/\D/g, "").replace(/^91/, "").length !== 10) return showMsg("Please enter a valid 10-digit phone number.", true);
    if (!course) return showMsg("Please pick your course.", true);
    if (typeof Razorpay === "undefined") return showMsg("Payment window could not load. Check your connection and try again.", true);

    setBusy(true, "Creating your order…");
    var order;
    try {
      order = await callFn("create-razorpay-order", {
        product: PRODUCT,
        student_name: name,
        student_email: email,
        student_phone: phone,
        course: course,
      });
    } catch (err) {
      setBusy(false);
      return showMsg("Could not start the payment. Please try again in a moment.", true);
    }

    var rzp = new Razorpay({
      key: order.key_id,
      amount: order.amount,
      currency: order.currency,
      name: "NaukriSala",
      description: "Onboarding fee — one-time",
      order_id: order.order_id,
      prefill: { name: name, email: email, contact: phone },
      theme: { color: "#0052ff" },
      modal: {
        ondismiss: function () {
          setBusy(false);
          showMsg("Payment cancelled — nothing was charged. You can try again when ready.", false);
        },
      },
      handler: async function (resp) {
        setBusy(true, "Verifying your payment…");
        try {
          var verified = await callFn("verify-razorpay-payment", {
            razorpay_order_id: resp.razorpay_order_id,
            razorpay_payment_id: resp.razorpay_payment_id,
            razorpay_signature: resp.razorpay_signature,
          });
          if (verified && verified.success) {
            setBusy(false);
            form.style.display = "none";
            document.getElementById("orderSummary").style.display = "none";
            showResult(verified);
          } else {
            throw new Error("verification_failed");
          }
        } catch (err) {
          setBusy(false);
          showMsg("We could not verify this payment. If money left your account, message us on WhatsApp with the Payment ID and we will check it — do not pay again yet.", true);
        }
      },
    });
    rzp.on("payment.failed", function (resp) {
      setBusy(false);
      var reason = (resp.error && resp.error.description) || "Payment failed.";
      showMsg(reason + " No money was taken for a failed payment. You can try again.", true);
    });
    rzp.open();
  });
})();
