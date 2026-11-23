/* Contact float — "Chat with us" (WhatsApp) + "Call me back" (tel) cluster.
   Replaces the Maya assistant widget (removed 2026-11-20, on Abhigyan's order).
   Numbers: WhatsApp +91 81206 94235 (site contact number); Call dials the same. */
(function () {
  var WA = 'https://wa.me/918120694235?text=' + encodeURIComponent('Hi NaukriSala!');
  var TEL = 'tel:+918120694235';
  var CHAT_SVG = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>';
  var PHONE_SVG = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z"/></svg>';
  var X_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg>';
  var wrap = document.createElement('div');
  wrap.className = 'cf-cluster cf-collapsed';
  wrap.id = 'cfCluster';
  wrap.innerHTML =
    '<a class="cf-row" href="' + WA + '" target="_blank" rel="noopener" aria-label="Chat with us on WhatsApp">' +
      '<span class="cf-label">Chat with us</span><span class="cf-btn">' + CHAT_SVG + '</span></a>' +
    '<a class="cf-row" href="' + TEL + '" aria-label="Call me back">' +
      '<span class="cf-label">Call me back</span><span class="cf-btn">' + PHONE_SVG + '</span></a>' +
    '<button class="cf-close" type="button" aria-label="Hide contact buttons">' + X_SVG + '</button>' +
    '<button class="cf-reopen" type="button" aria-label="Show contact buttons">' + CHAT_SVG + '</button>';
  document.body.appendChild(wrap);
  wrap.querySelector('.cf-close').addEventListener('click', function () { wrap.classList.add('cf-collapsed'); });
  wrap.querySelector('.cf-reopen').addEventListener('click', function () { wrap.classList.remove('cf-collapsed'); });
})();
