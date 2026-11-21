/* Placements & internships strip — renders window.NS_PLACEMENTS (built by
   tools/build_placements.py from track-record.html) into every
   .pl-strip section on course pages.
   Behaviour: auto-scrolls left on its own AND stays manually scrollable
   (drag / swipe / arrows / keyboard). Auto-scroll pauses while the user
   interacts and resumes a few seconds after they stop. */
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
      '" loading="lazy" decoding="async">' +
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
    track.innerHTML = half + '<div class="pl-dup" aria-hidden="true">' + half + '</div>';
    // Flatten: the duplicate wrapper's children join the same scroll flow.
    var dup = track.querySelector('.pl-dup');
    while (dup.firstChild) track.insertBefore(dup.firstChild, dup);
    dup.remove();

    var cards = track.querySelectorAll('.pl-card');
    if (!cards.length) return;
    var setWidth = 0;
    var halfCount = cards.length / 2;
    for (var i = 0; i < halfCount; i++) {
      setWidth += cards[i].getBoundingClientRect().width + 16; // 16px gap
    }
    var step = cards[0].getBoundingClientRect().width + 16;

    var paused = reduceMotion;
    var resumeTimer = null;
    var raf = null;
    var last = 0;

    function pause(ms) {
      paused = true;
      if (raf) { cancelAnimationFrame(raf); raf = null; }
      if (resumeTimer) clearTimeout(resumeTimer);
      if (!reduceMotion && ms) {
        resumeTimer = setTimeout(function () { paused = false; last = 0; tick(); }, ms);
      }
    }
    function tick(ts) {
      if (paused || reduceMotion) return;
      if (!last) last = ts;
      var dt = ts - last; last = ts;
      track.scrollLeft += (dt / 1000) * 36; // ~36px/s
      if (track.scrollLeft >= setWidth) track.scrollLeft -= setWidth;
      raf = requestAnimationFrame(tick);
    }
    function start() { if (!reduceMotion && !raf) { last = 0; raf = requestAnimationFrame(tick); } }

    // Pause while the pointer is over the strip; resume 3s after it leaves.
    section.addEventListener('mouseenter', function () { pause(0); });
    section.addEventListener('mouseleave', function () { pause(3000); });
    // Pause while dragging / touching; resume 3s after release.
    track.addEventListener('pointerdown', function () { pause(0); });
    window.addEventListener('pointerup', function () { pause(3000); });
    track.addEventListener('touchstart', function () { pause(0); }, { passive: true });
    track.addEventListener('touchend', function () { pause(3000); });
    // Stop entirely when the tab is hidden; resume when visible again.
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) pause(0); else pause(1500);
    });
    // Drag to scroll (mouse).
    var dragging = false, startX = 0, startLeft = 0, moved = 0;
    track.addEventListener('pointerdown', function (e) {
      if (e.pointerType === 'touch') return;
      dragging = true; moved = 0; startX = e.clientX; startLeft = track.scrollLeft;
      track.setPointerCapture(e.pointerId);
    });
    track.addEventListener('pointermove', function (e) {
      if (!dragging) return;
      var dx = e.clientX - startX;
      moved = Math.max(moved, Math.abs(dx));
      track.scrollLeft = startLeft - dx;
      if (track.scrollLeft >= setWidth) track.scrollLeft -= setWidth;
      if (track.scrollLeft < 0) track.scrollLeft += setWidth;
    });
    function endDrag() { if (dragging) { dragging = false; pause(3000); } }
    track.addEventListener('pointerup', endDrag);
    track.addEventListener('pointercancel', endDrag);
    track.addEventListener('click', function (e) {
      if (moved > 6) { e.preventDefault(); e.stopPropagation(); moved = 0; }
    }, true);
    // Arrows scroll by one card.
    function jump(dir) {
      pause(4000);
      var target = track.scrollLeft + dir * step;
      if (target >= setWidth) target -= setWidth;
      if (target < 0) target += setWidth;
      track.scrollTo({ left: target, behavior: 'smooth' });
    }
    if (prev) prev.addEventListener('click', function () { jump(-1); });
    if (next) next.addEventListener('click', function () { jump(1); });
    // Keep the loop seamless if the user scrolls manually to an edge.
    track.addEventListener('scroll', function () {
      if (track.scrollLeft >= setWidth) track.scrollLeft -= setWidth;
      else if (track.scrollLeft < 0) track.scrollLeft += setWidth;
    }, { passive: true });

    start();
  });
})();
