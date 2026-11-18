// verify-razorpay-payment — POST /functions/v1/verify-razorpay-payment
//
// Verifies a payment the checkout modal reports as successful.
// A payment is marked paid ONLY when BOTH checks pass:
//   1. HMAC-SHA256(order_id + "|" + payment_id, KEY_SECRET) matches the
//      signature the browser sends (proves the callback is genuinely
//      from Razorpay's checkout for this order).
//   2. A server-side GET to Razorpay confirms the payment is 'captured',
//      belongs to this order, and the amount matches the order amount.
// The frontend callback alone is NEVER trusted.
//
// Idempotent: if the order is already 'paid', it returns success again
// without re-processing (safe for retries and browser refreshes).
//
// Body: { razorpay_order_id, razorpay_payment_id, razorpay_signature }
// Returns: { success: true, payment_id, order_id, amount, course }
// Errors: 400 missing fields / unknown order / signature mismatch / not captured.
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import {
  corsHeaders,
  getEnv,
  handleOptions,
  hmacSha256Hex,
  json,
  razorpayAuth,
  safeEqual,
  supabaseService,
} from "../_shared/razorpay.ts";

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

  const order_id = String(body.razorpay_order_id ?? "").trim();
  const payment_id = String(body.razorpay_payment_id ?? "").trim();
  const signature = String(body.razorpay_signature ?? "").trim();
  if (!order_id || !payment_id || !signature) {
    return json({ success: false, error: "missing_fields" }, 400, headers);
  }

  const sb = supabaseService();

  const { data: row, error: rowErr } = await sb
    .from("ns_payments")
    .select("id, student_email, course, amount_paise, currency, status")
    .eq("razorpay_order_id", order_id)
    .maybeSingle();
  if (rowErr || !row) {
    return json({ success: false, error: "unknown_order" }, 400, headers);
  }

  // Already verified — return success without doing anything twice.
  if (row.status === "paid") {
    return json({
      success: true,
      payment_id,
      order_id,
      amount: row.amount_paise,
      course: row.course,
      already_verified: true,
    }, 200, headers);
  }

  // 1. Signature check.
  const expected = await hmacSha256Hex(
    getEnv("RAZORPAY_KEY_SECRET"),
    `${order_id}|${payment_id}`,
  );
  if (!safeEqual(expected, signature)) {
    await sb.from("ns_payments").update({
      status: "failed",
      failure_reason: "signature_mismatch",
      updated_at: new Date().toISOString(),
    }).eq("razorpay_order_id", order_id);
    return json({ success: false, error: "signature_mismatch" }, 400, headers);
  }

  // 2. Server-side confirmation from Razorpay (amount + status + order).
  const rzpRes = await fetch(`https://api.razorpay.com/v1/payments/${payment_id}`, {
    headers: { Authorization: razorpayAuth() },
  });
  const payment = await rzpRes.json();
  if (!rzpRes.ok || !payment.id) {
    console.error("Razorpay payment fetch failed:", rzpRes.status);
    return json({ success: false, error: "payment_lookup_failed" }, 502, headers);
  }
  if (payment.status !== "captured") {
    await sb.from("ns_payments").update({
      status: "failed",
      failure_reason: `payment_not_captured:${payment.status}`,
      updated_at: new Date().toISOString(),
    }).eq("razorpay_order_id", order_id);
    return json({ success: false, error: "payment_not_captured", status: payment.status }, 400, headers);
  }
  if (payment.order_id !== order_id || payment.amount !== row.amount_paise) {
    await sb.from("ns_payments").update({
      status: "failed",
      failure_reason: "amount_or_order_mismatch",
      updated_at: new Date().toISOString(),
    }).eq("razorpay_order_id", order_id);
    return json({ success: false, error: "amount_or_order_mismatch" }, 400, headers);
  }

  // Mark paid. If a webhook already marked it paid first, this update is
  // a no-op for the status (already 'paid' is handled above on re-runs).
  const paidAt = new Date().toISOString();
  const { error: updErr } = await sb.from("ns_payments").update({
    status: "paid",
    razorpay_payment_id: payment_id,
    paid_at: paidAt,
    updated_at: paidAt,
  }).eq("razorpay_order_id", order_id).eq("status", "created");
  if (updErr) {
    console.error("ns_payments update failed:", updErr.message);
    return json({ success: false, error: "db_update_failed" }, 500, headers);
  }

  // Link the payment to the student record: onboarding fee now paid.
  await sb.from("ns_students").update({ fee_status: "paid" })
    .eq("email", row.student_email);

  return json({
    success: true,
    payment_id,
    order_id,
    amount: row.amount_paise,
    currency: row.currency,
    course: row.course,
  }, 200, headers);
});
