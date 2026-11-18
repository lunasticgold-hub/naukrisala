// create-razorpay-order — POST /functions/v1/create-razorpay-order
//
// Creates a Razorpay order for the NaukriSala onboarding fee.
// The amount is NEVER taken from the browser: the frontend sends only a
// product code, and the price is looked up server-side in PRICE_CATALOG.
// Also inserts a row in ns_payments (status 'created') and returns the
// public key ID + order ID the checkout modal needs.
//
// Body: { product, student_name, student_email, student_phone, course }
// Returns: { order_id, amount, currency, key_id }
// Errors: 400 validation, 502 Razorpay API failure, 500 other.
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import {
  corsHeaders,
  getEnv,
  handleOptions,
  json,
  razorpayAuth,
  supabaseService,
} from "../_shared/razorpay.ts";

// Server-side price catalog (paise). Change ONE line here when the
// onboarding fee changes — the frontend never sends an amount.
// NOTE: site publishes ₹15,000; the ₹15,000 vs ₹20,000 question is still
// open with the owner. Until he decides, the published ₹15,000 applies.
const PRICE_CATALOG: Record<string, { amount: number; currency: string; label: string }> = {
  onboarding: { amount: 1500000, currency: "INR", label: "NaukriSala onboarding fee" },
};

// A fresh order is not created if the same student already has an unpaid
// order for the same product from the last 15 minutes (double-click guard).
const IDEMPOTENCY_WINDOW_MINUTES = 15;

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function cleanPhone(raw: string): string {
  const digits = raw.replace(/\D/g, "");
  return digits.startsWith("91") && digits.length === 12 ? digits.slice(2) : digits;
}

serve(async (req) => {
  const preflight = handleOptions(req);
  if (preflight) return preflight;
  const headers = corsHeaders(req);

  if (req.method !== "POST") {
    return json({ error: "method_not_allowed" }, 405, headers);
  }

  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return json({ error: "invalid_json" }, 400, headers);
  }

  const product = String(body.product ?? "").trim();
  const student_name = String(body.student_name ?? "").trim();
  const student_email = String(body.student_email ?? "").trim().toLowerCase();
  const student_phone = cleanPhone(String(body.student_phone ?? ""));
  const course = String(body.course ?? "").trim();

  const price = PRICE_CATALOG[product];
  if (!price) return json({ error: "unknown_product" }, 400, headers);
  if (price.amount < 100) return json({ error: "amount_below_minimum" }, 400, headers);
  if (student_name.length < 2) return json({ error: "invalid_name" }, 400, headers);
  if (!EMAIL_RE.test(student_email)) return json({ error: "invalid_email" }, 400, headers);
  if (student_phone.length !== 10) return json({ error: "invalid_phone" }, 400, headers);
  if (course.length < 2) return json({ error: "invalid_course" }, 400, headers);

  const sb = supabaseService();

  // Reuse a recent unpaid order for the same student + product.
  const since = new Date(Date.now() - IDEMPOTENCY_WINDOW_MINUTES * 60_000).toISOString();
  const { data: existing } = await sb
    .from("ns_payments")
    .select("razorpay_order_id, amount_paise, currency")
    .eq("student_email", student_email)
    .eq("product", product)
    .eq("status", "created")
    .gte("created_at", since)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();
  if (existing) {
    return json({
      order_id: existing.razorpay_order_id,
      amount: existing.amount_paise,
      currency: existing.currency,
      key_id: getEnv("RAZORPAY_KEY_ID"),
      reused: true,
    }, 200, headers);
  }

  const receipt = `NS-ONB-${Date.now().toString(36).toUpperCase()}`;

  // Create the order with Razorpay.
  const rzpRes = await fetch("https://api.razorpay.com/v1/orders", {
    method: "POST",
    headers: {
      Authorization: razorpayAuth(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      amount: price.amount,
      currency: price.currency,
      receipt,
      notes: {
        product,
        student_name,
        student_email,
        course,
      },
    }),
  });
  const rzp = await rzpRes.json();
  if (!rzpRes.ok || !rzp.id) {
    console.error("Razorpay order failed:", rzpRes.status, JSON.stringify(rzp).slice(0, 500));
    return json({ error: "razorpay_order_failed" }, 502, headers);
  }

  // Record the payment attempt (status 'created' — NOT paid yet).
  const { error: dbErr } = await sb.from("ns_payments").insert({
    student_name,
    student_email,
    student_phone,
    course,
    product,
    amount_paise: price.amount,
    currency: price.currency,
    receipt,
    razorpay_order_id: rzp.id,
    status: "created",
  });
  if (dbErr) {
    console.error("ns_payments insert failed:", dbErr.message);
    return json({ error: "db_insert_failed" }, 500, headers);
  }

  return json({
    order_id: rzp.id,
    amount: price.amount,
    currency: price.currency,
    key_id: getEnv("RAZORPAY_KEY_ID"),
  }, 200, headers);
});
