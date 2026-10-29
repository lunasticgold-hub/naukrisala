#!/usr/bin/env python3
"""Static regression guard for the home testimonials marquee (no browser needed).

Catches the 2026-10-30 mistake class: a layout-container class name reused on a
text element, so the label inherited the scrolling track's display/width/animation
and slid over neighbouring text on maximised screens.

Run after any home.css marquee change, before pushing. Exits non-zero on failure.
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
css = (ROOT / 'home.css').read_text(encoding='utf-8')
css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)  # strip comments
html = (ROOT / 'index.html').read_text(encoding='utf-8')
fails = []

def check(name, ok, detail=''):
    print(('PASS' if ok else 'FAIL'), '-', name, detail)
    if not ok:
        fails.append(name)

# 1. No bare .review-track rule may carry layout/animation properties.
# (A selector counts as bare only if it IS exactly `.review-track`; scoped
# selectors like `.review-marquee > .review-track` are the fix, not the bug.)
bare_bad = []
for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', css):
    selectors = [x.strip() for x in m.group(1).split(',')]
    if '.review-track' not in selectors:
        continue
    body = m.group(2)
    bad = [p for p in ('display', 'width', 'animation') if re.search(rf'(^|;)\s*{p}\s*:', body)]
    # animation:none (reduced-motion guard) is allowed
    if 'animation' in bad and 'animation:none' in body.replace(' ', ''):
        bad.remove('animation')
    if bad:
        bare_bad.append(f"{m.group(1).strip()} -> {body.strip()[:80]}")
check('no bare .review-track layout/animation rule', not bare_bad, '; '.join(bare_bad))

# 2. Scrolling container is direct-child scoped and still animated.
flat = css.replace(' ', '')
check('container scoped to .review-marquee > .review-track',
      '.review-marquee>.review-track{display:flex;width:max-content;animation:review-scroll' in flat)
check('hover pause scoped to direct child',
      '.review-marquee:hover>.review-track{animation-play-state:paused}' in css.replace(' ', ''))

# 3. Card label is an explicit non-animated wrapping paragraph.
m = re.search(r'\.review-card\s+\.review-track\s*\{([^}]*)\}', css)
body = m.group(1).replace(' ', '') if m else ''
check('label reset exists (block, auto width, no animation)',
      m is not None and 'display:block' in body and 'width:auto' in body and 'animation:none' in body)

# 4. Fluid sizing + breakpoints intact.
check('fluid card widths (cqw) + breakpoints present',
      '100cqw' in css and 'max-width:1023px' in css and 'max-width:639px' in css)

# 5. Markup shape unchanged: 1 track container + 48 card labels.
check('markup: 1 track container + 48 labels',
      html.count('<div class="review-track">') == 1 and html.count('<p class="review-track">') == 48,
      f"divs={html.count(chr(60)+'div class=\"review-track\"'+chr(62))} labels={html.count(chr(60)+'p class=\"review-track\"'+chr(62))}")

print('RESULT:', 'ALL PASS' if not fails else f"{len(fails)} FAILING: {', '.join(fails)}")
sys.exit(1 if fails else 0)
