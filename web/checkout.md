# Checkout (Stripe TEST mode only)

No live key anywhere in this repo. The test key is read from the environment variable `STRIPE_TEST_KEY` and is never committed.

## Flow
1. Create a Payment Link in the Stripe dashboard in TEST mode: product "A new, checked lemma" at $29 (and "Printed proof pack" at $79, text only for now).
2. Add a custom field "Name for the certificate" and map it to session metadata key `buyer_name` (Payment Links: `metadata[buyer_name]` via a custom text field, or create the Checkout Session server-side with `metadata={"buyer_name": ...}`).
3. Point a webhook endpoint at your server for `checkout.session.completed`. The handler MUST verify the `Stripe-Signature` header (webhook signing secret from env, never committed) before anything else.
4. The handler passes the verified event to `tools/fulfil.py` (`fulfil(event, "stock")`): it refuses live-mode events, unpaid sessions, missing names and repeated session ids, then runs `claim` on the next reserved serial. No Lean run happens at purchase time; the lemma was checked when it entered stock.
5. Email or show the buyer `stock/<serial>.pdf` and the command `python -m buyatheorem verify <serial> --dir stock`.

## Local test (no network)
    python tools/fulfil.py tests/fixtures/checkout_completed.json --dir stock

Exit codes: 0 fulfilled, 2 bad event, 3 already fulfilled, 4 stock empty.
Test key use: `export STRIPE_TEST_KEY=...` in your shell only, for the Stripe CLI (`stripe listen --api-key "$STRIPE_TEST_KEY"`).
