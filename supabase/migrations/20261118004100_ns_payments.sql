-- NaukriSala payments — Razorpay Standard Checkout (test mode first)
-- Run in the Supabase SQL editor (project ccibsfsnnyqdazomwrbw) or:
--   supabase db push   (after `supabase link --project-ref ccibsfsnnyqdazomwrbw`)
--
-- Design:
--   * ns_payments holds one row per Razorpay order. Status is 'created'
--     until the verify function or the webhook confirms a capture.
--   * ns_payment_events records every verified webhook delivery, once
--     per (payment_id, event) — that unique pair is the idempotency key.
--   * RLS is ON with no public write access. Only the service role
--     (used by the Edge Functions) can insert/update. Authenticated
--     users (the admin, signed in) can read, matching the other ns_*
--     tables. Students can never change a payment status.

create table if not exists public.ns_payments (
  id uuid primary key default gen_random_uuid(),
  student_id uuid references public.ns_students(id),
  student_name text not null,
  student_email text not null,
  student_phone text,
  course text,
  product text not null default 'onboarding',
  amount_paise integer not null check (amount_paise >= 100),
  currency text not null default 'INR',
  receipt text,
  razorpay_order_id text not null unique,
  razorpay_payment_id text,
  status text not null default 'created'
    check (status in ('created', 'paid', 'failed', 'refunded')),
  failure_reason text,
  paid_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists ns_payments_email_idx
  on public.ns_payments (student_email);
create index if not exists ns_payments_status_idx
  on public.ns_payments (status);

create table if not exists public.ns_payment_events (
  id uuid primary key default gen_random_uuid(),
  razorpay_payment_id text not null,
  event text not null,
  payload jsonb not null,
  received_at timestamptz not null default now(),
  unique (razorpay_payment_id, event)
);

alter table public.ns_payments enable row level security;
alter table public.ns_payment_events enable row level security;

-- Admin (signed-in) can read payments and webhook events. Nobody except
-- the service role (Edge Functions) can write — no INSERT/UPDATE/DELETE
-- policy exists for any other role.
drop policy if exists "ns_payments_admin_read" on public.ns_payments;
create policy "ns_payments_admin_read"
  on public.ns_payments for select
  to authenticated
  using (true);

drop policy if exists "ns_payment_events_admin_read" on public.ns_payment_events;
create policy "ns_payment_events_admin_read"
  on public.ns_payment_events for select
  to authenticated
  using (true);
