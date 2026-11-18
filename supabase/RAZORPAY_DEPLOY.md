# Razorpay Standard Checkout — deploy & test guide (NaukriSala)

Test mode first. Nothing here takes real money until the secrets are
switched to LIVE keys and the merchant account is activated.

## What was built

| File | What it does |
| --- | --- |
| `supabase/functions/_shared/razorpay.ts` | HMAC-SHA256, Basic auth, Supabase service client, CORS, JSON helpers |
| `supabase/functions/create-razorpay-order/index.ts` | Creates the Razorpay order. Price comes from a server-side catalog (onboarding = ₹15,000 / 1,500,000 paise) — the browser never sends an amount. Reuses a recent unpaid order for the same student (double-click guard). Inserts `ns_payments` (status `created`). |
| `supabase/functions/verify-razorpay-payment/index.ts` | Checks the HMAC signature, then confirms with Razorpay that the payment is `captured`, for this order, for the exact amount. Only then marks `paid` and sets `ns_students.fee_status = 'paid'`. Idempotent. |
| `supabase/functions/razorpay-webhook/index.ts` | Verifies the webhook signature, records each `(payment_id, event)` once in `ns_payment_events`, handles `payment.captured` / `payment.failed`. Duplicate deliveries are ignored. |
| `supabase/migrations/20261118004100_ns_payments.sql` | `ns_payments` + `ns_payment_events` tables, RLS on, admin read-only. Only the service role (Edge Functions) can write. |
| `pay.js` | Fees-page checkout: form → create order → Razorpay modal → verify → success screen. Disables the button while busy, handles modal dismiss and `payment.failed`. |
| `fees.html` | New "Pay your onboarding fee" section after the fee table + `checkout.js` and `pay.js` scripts. |

## 1. Secrets (do this first — values never go in the repo)

In the Supabase dashboard: **Project → Edge Functions → Secrets** (or
`supabase secrets set KEY=value` from the CLI). Set these three:

- `RAZORPAY_KEY_ID` — from Razorpay Dashboard → Settings → API Keys.
  Use the **Test Mode** key ID while testing.
- `RAZORPAY_KEY_SECRET` — the matching Test Mode key secret.
- `RAZORPAY_WEBHOOK_SECRET` — created in step 4 below (set it after
  creating the webhook; the webhook function needs it to verify events).

If the test keys were copied from somewhere other than your own Razorpay
dashboard, use the dashboard's own test keys instead — test orders belong
to whichever account the keys came from.

## 2. Database — run the migration

Supabase dashboard → **SQL Editor** → paste
`supabase/migrations/20261118004100_ns_payments.sql` → Run.
Or with the CLI: `supabase link --project-ref ccibsfsnnyqdazomwrbw`
then `supabase db push`.

Verify: `ns_payments` and `ns_payment_events` appear in Table Editor,
RLS enabled, no public write policies.

## 3. Deploy the Edge Functions

No Supabase CLI is installed on this machine yet. Install it, then:

```bash
npm install -g supabase
supabase login            # needs your Supabase access token (dashboard login)
supabase link --project-ref ccibsfsnnyqdazomwrbw
supabase functions deploy create-razorpay-order
supabase functions deploy verify-razorpay-payment
supabase functions deploy razorpay-webhook
```

Function URLs (after deploy):

- `https://ccibsfsnnyqdazomwrbw.supabase.co/functions/v1/create-razorpay-order`
- `https://ccibsfsnnyqdazomwrbw.supabase.co/functions/v1/verify-razorpay-payment`
- `https://ccibsfsnnyqdazomwrbw.supabase.co/functions/v1/razorpay-webhook`

## 4. Webhook (Razorpay dashboard)

Razorpay Dashboard → Settings → Webhooks → Add New Webhook:

- URL: `https://ccibsfsnnyqdazomwrbw.supabase.co/functions/v1/razorpay-webhook`
- Events: `payment.captured`, `payment.failed`
- Copy the webhook secret it shows → set it as `RAZORPAY_WEBHOOK_SECRET`
  in Supabase Edge Function secrets (step 1).

## 5. Commit + push the site changes

The fees page + `pay.js` + `supabase/` files are written but **not
committed** — the nightly jobs refresh is mid-run and a push-watch is
waiting to push the Phase 2 SEO + refund-policy commits first.
Commit after that push clears:

```bash
cd ~/workspace/naukrisala-site
git add supabase pay.js fees.html
git commit -m "Razorpay Standard Checkout via Supabase Edge Functions (test mode)"
git push
```

Wait ~2–3 minutes for GitHub Pages, then open
`https://naukrisala.in/fees.html` and check the Pay section renders.

## 6. Test checklist (test mode — use Razorpay's test cards/UPI)

1. **Successful payment** — fill the form, pay with a test UPI/card.
   Expect: success screen with Payment ID; `ns_payments` row `paid`;
   `ns_students.fee_status = 'paid'` for that email (if the student exists).
2. **Failed payment** — use a failing test card. Expect: error message,
   button re-enabled, row stays `created` or becomes `failed`, no double charge.
3. **Invalid signature** — call `verify-razorpay-payment` with a wrong
   signature (curl). Expect: 400 `signature_mismatch`, row `failed`.
4. **Duplicate verify** — call verify twice with the same valid payload.
   Expect: second call returns success with `already_verified: true`,
   still exactly one `paid` row.
5. **Duplicate webhook** — re-send the same `payment.captured` event
   (dashboard → Webhooks → replay, or curl with the same body+signature).
   Expect: second delivery returns `{ ok: true, duplicate: true }`,
   no second event row.
6. **Browser refresh after payment** — refresh the success screen.
   Expect: no re-charge, no duplicate order (the form is hidden after success).
7. **Delayed verification** — close the tab right after the modal succeeds
   but before verify returns; the webhook's `payment.captured` should
   still mark the row `paid` within seconds.
8. **Amount tampering** — POST `create-razorpay-order` with an `amount`
   field in the body. Expect: it is ignored; the order is always ₹15,000.

## 7. Going live (only after the merchant account is activated)

1. Finish Razorpay KYC (account activation).
2. In Supabase secrets, replace the test `RAZORPAY_KEY_ID` /
   `RAZORPAY_KEY_SECRET` with the **Live Mode** keys.
3. In the Razorpay dashboard, create the webhook again in Live Mode
   (or switch the existing one) and update `RAZORPAY_WEBHOOK_SECRET`.
4. Do one real ₹15,000 test payment yourself, then refund it from the
   Razorpay dashboard, and confirm the row flips to `paid` then `refunded`
   only via dashboard action (the code never marks refunds automatically).

## Open decision (needs the owner)

- **Amount: ₹15,000 vs ₹20,000.** The code uses the site's published
  ₹15,000. If the real onboarding fee is ₹20,000, change one line in
  `supabase/functions/create-razorpay-order/index.ts`
  (`PRICE_CATALOG.onboarding.amount` → `2000000`) and the button label
  in `fees.html` / `pay.js`, then redeploy the function.

## Checkout page + Courses dropdown (18 Nov 2026, after the first deploy)

- `checkout.html` + `checkout.js` — a proper checkout page. Every Pay fees
  button links here as `checkout.html?course=<name>`; the page shows the
  course in the order summary and locks it in (unknown/missing course shows
  the same course picker as fees.html). Same flow as `pay.js`: server-side
  price (flat ₹15,000 onboarding), Razorpay modal, server-side verify.
  `checkout.html` is `noindex` and excluded from `sitemap_gen.py`
  (sitemap stays at 123 URLs).
- Courses nav dropdown — built by `initCoursesDropdown()` in `script.js`
  (no per-page HTML edits; every page that loads script.js gets it).
  Left: 4 domains (Finance & Compliance, Data & AI, Software Development,
  Enterprise Apps & Ops). Right: the domain's courses with duration +
  placement range, a Details link, and a Pay fees button each.
- Pay fees buttons also on all 15 course cards (`renderCourses` in
  `script.js`), the featured AML card on `courses.html`, and the hero of
  all 5 course pages. All charge the same flat ₹15,000 onboarding fee;
  the course name is recorded in `ns_payments.course`.
- `index.html`: both "Highest package ₹36 LPA" peak banners removed on
  the owner's order (18 Nov). The figure still appears in the home stats
  block, the partners fine print, the FAQ, and on track-record.html.
