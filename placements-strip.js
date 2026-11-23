/* Placements strip — renders window.NS_PLACEMENTS (built by
   tools/build_placements.py from track-record.html) into every
   .pl-strip section on course pages.
   Behaviour: auto-scrolls left on its own AND stays manually scrollable
   (drag / swipe / arrows / keyboard). Auto-scroll pauses only while the
   user is actively dragging or right after an arrow tap, then resumes —
   merely hovering the strip does NOT stop it. */
(function () {
  var data = window.NS_PLACEMENTS || [];
  var sections = document.querySelectorAll('.pl-strip');
  if (!sections.length || !data.length) return;
  var reduceMotion = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function cardHTML(p) {
    return '<article class="pl-card">' +
      '<img class="pl-photo" src="' + esc(p.photo) + '" alt="' + esc(p.name) +
      '" loading="lazy" decoding="async" draggable="false">' +
      '<h3 class="pl-name">' + esc(p.name) + '</h3>' +
      (p.after ? '<p class="pl-after">' + esc(p.after) + '</p>' : '') +
      '<p class="pl-meta">' + esc([p.track, p.placed].filter(Boolean).join(' · ')) + '</p>' +
      '</article>';
  }

  sections.forEach(function (section) {
    var track = section.querySelector('.pl-track');
    var prev = section.querySelector('.pl-prev');
    var next = section.querySelector('.pl-next');
    if (!track) return;
    var countEl = section.querySelector('[data-pl-count]');
    if (countEl) countEl.textContent = data.length;

    var half = data.map(cardHTML).join('');
    track.innerHTML = half + half;
    var cards = track.querySelectorAll('.pl-card');
    if (!cards.length) return;
    var halfCount = cards.length / 2;
    // Exact width of one set (incl. gaps): distance between the first card
    // of each copy. This is what the loop wraps on, so the seam is invisible.
    var setWidth = cards[halfCount].offsetLeft - cards[0].offsetLeft;
    var step = cards[0].getBoundingClientRect().width + 16; // card + gap

    var paused = reduceMotion;
    var resumeTimer = null;
    var raf = null;
    var last = 0;

    function loop(ts) {
      raf = null;
      if (paused || reduceMotion) return;
      if (!last) last = ts;
      var dt = ts - last; last = ts;
      if (dt > 250) dt = 250; // tab was hidden/throttled — no big jump
      track.scrollLeft += (dt / 1000) * 20; // ~20px/s — slow drift, right to left
      if (track.scrollLeft >= setWidth) track.scrollLeft -= setWidth;
      raf = requestAnimationFrame(loop);
    }
    function start() {
      if (reduceMotion || raf) return;
      last = 0;
      raf = requestAnimationFrame(loop);
    }
    function pause(ms) {
      paused = true;
      if (raf) { cancelAnimationFrame(raf); raf = null; }
      if (resumeTimer) clearTimeout(resumeTimer);
      if (!reduceMotion && ms) {
        resumeTimer = setTimeout(function () { paused = false; start(); }, ms);
      }
    }
    // Keep the loop seamless if the user scrolls manually to an edge.
    track.addEventListener('scroll', function () {
      if (track.scrollLeft >= setWidth) track.scrollLeft -= setWidth;
      else if (track.scrollLeft < 0) track.scrollLeft += setWidth;
    }, { passive: true });

    // Drag to scroll (mouse). Touch scrolls natively; pause auto-scroll
    // while the finger is down and resume after release.
    var dragging = false, startX = 0, startLeft = 0, moved = 0;
    track.addEventListener('pointerdown', function (e) {
      if (e.pointerType === 'touch') { pause(0); return; }
      dragging = true; moved = 0; startX = e.clientX; startLeft = track.scrollLeft;
      pause(0);
      try { track.setPointerCapture(e.pointerId); } catch (err) { /* ignore */ }
    });
    track.addEventListener('pointermove', function (e) {
      if (!dragging) return;
      var dx = e.clientX - startX;
      moved = Math.max(moved, Math.abs(dx));
      track.scrollLeft = startLeft - dx;
    });
    function endDrag() {
      if (!dragging && !paused) return;
      dragging = false;
      pause(3000);
    }
    track.addEventListener('pointerup', endDrag);
    track.addEventListener('pointercancel', endDrag);
    track.addEventListener('touchstart', function () { pause(0); }, { passive: true });
    track.addEventListener('touchend', function () { pause(3000); });
    track.addEventListener('click', function (e) {
      if (moved > 6) { e.preventDefault(); e.stopPropagation(); moved = 0; }
    }, true);
    // Arrows scroll by one card, then auto-scroll resumes.
    function jump(dir) {
      pause(4000);
      var target = track.scrollLeft + dir * step;
      if (target >= setWidth) target -= setWidth;
      if (target < 0) target += setWidth;
      track.scrollTo({ left: target, behavior: 'smooth' });
    }
    if (prev) prev.addEventListener('click', function () { jump(-1); });
    if (next) next.addEventListener('click', function () { jump(1); });
    // Stop entirely when the tab is hidden; resume shortly after it returns.
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) pause(0); else pause(1500);
    });

    start();
  });
})();
