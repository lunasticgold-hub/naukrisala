// razorpay-webhook — POST /functions/v1/razorpay-webhook
//
// Receives Razorpay webhook events (payment.captured, payment.failed).
// Security:
//   - The signature in X-Razorpay-Signature is verified against the raw
//     request body using RAZORPAY_WEBHOOK_SECRET. Unverified calls are
//     rejected with 400 and nothing is written.
//   - Idempotency: each (payment_id, event) pair is recorded once in
//     ns_payment_events (unique constraint). A duplicate delivery —
//     Razorpay retries up to 3 times on non-2xx — is acknowledged with
//     200 and ignored, so a payment is never double-recorded.
//   - Always returns 200 for verified events, even unknown ones, so
//     Razorpay stops retrying.
//
// Webhook URL to configure in the Razorpay dashboard:
//   https://ccibsfsnnyqdazomwrbw.supabase.co/functions/v1/razorpay-webhook
// Events to subscribe: payment.captured, payment.failed
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import {
  getEnv,
  hmacSha256Hex,
  json,
  safeEqual,
  supabaseService,
} from "../_shared/razorpay.ts";

serve(async (req) => {
  if (req.method !== "POST") {
    return json({ error: "method_not_allowed" }, 405);
  }

  // Raw body is required: the signature is computed over the exact bytes.
  const rawBody = await req.text();
  const signature = req.headers.get("X-Razorpay-Signature") ?? "";
  const expected = await hmacSha256Hex(getEnv("RAZORPAY_WEBHOOK_SECRET"), rawBody);
  if (!signature || !safeEqual(expected, signature)) {
    console.error("Webhook signature verification failed");
    return json({ error: "invalid_signature" }, 400);
  }

  let event: Record<string, unknown>;
  try {
    event = JSON.parse(rawBody);
  } catch {
    return json({ error: "invalid_json" }, 400);
  }

  const eventType = String(event.event ?? "");
  const payment = (event.payload as Record<string, unknown> | undefined)
    ?.payment as Record<string, unknown> | undefined;
  const entity = (payment?.entity ?? {}) as Record<string, unknown>;
  const paymentId = String(entity.id ?? "");
  const orderId = String(entity.order_id ?? "");
  if (!eventType || !paymentId) {
    return json({ ok: true, ignored: "no_payment_entity" });
  }

  const sb = supabaseService();

  // Idempotency: record the event first. A duplicate delivery hits the
  // unique constraint and is acknowledged without re-processing.
  const { error: evtErr } = await sb.from("ns_payment_events").insert({
    razorpay_payment_id: paymentId,
    event: eventType,
    payload: event,
  });
  if (evtErr) {
    if (evtErr.code === "23505") {
      return json({ ok: true, duplicate: true });
    }
    console.error("ns_payment_events insert failed:", evtErr.message);
    return json({ error: "db_insert_failed" }, 500);
  }

  const now = new Date().toISOString();

  if (eventType === "payment.captured") {
    const { error } = await sb.from("ns_payments").update({
      status: "paid",
      razorpay_payment_id: paymentId,
      paid_at: now,
      updated_at: now,
    }).eq("razorpay_order_id", orderId).eq("status", "created");
    if (error) console.error("webhook captured update failed:", error.message);
    else {
      // Keep the student record in sync (same as the verify function).
      const { data: row } = await sb.from("ns_payments")
        .select("student_email")
        .eq("razorpay_order_id", orderId)
        .maybeSingle();
      if (row) {
        await sb.from("ns_students").update({ fee_status: "paid" }).eq("email", row.student_email);
      }
    }
  } else if (eventType === "payment.failed") {
    const err = (entity.error_description as string | undefined)
      ?? (entity.error_code as string | undefined)
      ?? "payment_failed";
    const { error } = await sb.from("ns_payments").update({
      status: "failed",
      failure_reason: String(err).slice(0, 300),
      updated_at: now,
    }).eq("razorpay_order_id", orderId).eq("status", "created");
    if (error) console.error("webhook failed update failed:", error.message);
  }
  // Other event types are recorded in ns_payment_events and ignored.

  return json({ ok: true });
});
