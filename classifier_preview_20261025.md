# Classifier snippet-fallback preview — 2026-10-25 (DRY RUN, board untouched)

Method: for each tagged (non-General) job, re-ran `fetch_browser_boards.classify`
with the title only (`classify(title, "")`). If the title alone does not
reproduce the stored tag, the tag is "snippet/description-dependent".

## Headline
- Tagged jobs: 2,771 | snippet-dependent: 470 (17%)
  - retag-derived: 455 | exempt-source (browser-boards/aml-boards): 15
- Strict title-only gating would move 470 jobs to General. NOT recommended
  as a blind switch — see why below.

## Per-course table (tagged / snip-dep / stay / move)
| course | tagged | snip-dep | stay | move |
|---|---|---|---|---|
| aml-kyc | 567 | 259 | 308 | 259 |
| java-fullstack | 346 | 15 | 331 | 15 |
| data-science-ai | 253 | 7 | 246 | 7 |
| qa-testing | 236 | 16 | 220 | 16 |
| dbi | 223 | 12 | 211 | 12 |
| python-fullstack | 202 | 26 | 176 | 26 |
| data-analyst | 147 | 8 | 139 | 8 |
| servicenow | 145 | 14 | 131 | 14 |
| dotnet | 122 | 5 | 117 | 5 |
| workday | 122 | 17 | 105 | 17 |
| web-dev | 96 | 6 | 90 | 6 |
| ib-operations | 91 | 61 | 30 | 61 |
| sap-fico | 88 | 9 | 79 | 9 |
| stom | 75 | 8 | 67 | 8 |
| power-bi | 58 | 7 | 51 | 7 |

## Why the blunt switch is wrong
- AML's 259 are BY DESIGN: aml_gate v2 passes adjacent titles only with AML
  context in the description. Those are the gate working, not over-matches.
- Most sampled snippet-dependent tags look plausibly correct: the snippet
  supplies the disambiguating detail the title lacks (Python for a generic
  "Full Stack Developer" title; ".NET" for "Dot Net Developer" wording;
  IB context for "Trade Lifecycle Analyst" / "Payment Lifecycle Associate").
- The genuine over-matches are narrow pockets, e.g. STOM's 8 ("Technical
  Architect - Microservices", "Project Manager - Agile", "Senior
  Information Security Analyst") — generic tech roles likely tagged via
  vague "service delivery/management" snippet phrases — plus scattered
  weak ones in servicenow/workday ("Digitalization Consultant",
  "Consultant - ITGC", "Talent Product Specialist").

## Recommendation (needs user approval before any board change)
Do NOT flip strict title-only gating board-wide. Instead, tighten the
specific vague phrases per track (AML-v2 style: strong title anchors pass,
adjacent titles need track context, generic titles fail), starting with
STOM's "service delivery/management" phrase, then re-preview. The 470
figure is the upper bound of what could move, not the target.
