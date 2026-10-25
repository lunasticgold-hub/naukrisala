# Internal linking — NaukriSala site (standing rule)

- Every page is in the nav + footer (Blog included) and in sitemap.xml.
- Every content page carries a "Related:" strip before `</main>`, linking to 2–3
  genuinely related pages (course ↔ jobs board ↔ blog track ↔ track record ↔ tools).
- Every blog post carries Related links from its track (mapping in
  tools/generate_blog.py), and the blog index supports `#<track-slug>` links
  (e.g. blog.html#aml-kyc) so course and tool pages can link to a filtered view.
- Home carries a "From the blog" strip (3 posts) + "Read all 100 posts".
- Legal pages (terms, privacy) stay clean: nav + footer links only, no strip.
- When adding a page or section: add it to nav + footer + sitemap, give it a
  Related strip, and link to it from at least 2 existing pages. After any
  chrome change, regenerate blog pages with tools/generate_blog.py so all 100
  posts stay in sync.
