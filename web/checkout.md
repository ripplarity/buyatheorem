# Checkout (Stripe TEST mode only)

No live key anywhere in this repo. The test key is read from the environment variable `STRIPE_TEST_KEY` and is never committed. Object ids below are not secrets.

## Test objects (livemode=false)
- Product: `prod_VatW5FsUdP1uSX`
- Price: `price_1UZhjhAEYFnTYpgASNYATWfZ` ($29)
- Payment link: https://buy.stripe.com/test_aFadR8dm7dSW0Fn7v45Rm00
- Payment link id: `plink_1UZhjiAEYFnTYpgAkqQ7MbPE` (default filter for `fulfil.py --poll`; override with `--link`).
- Custom text field key `buyer_name`, label "Name for the certificate (becomes public)".

## Flow
1. The buyer pays through the payment link and fills in the name field.
2. Until a webhook endpoint exists, the operator runs fulfilment by hand:

        STRIPE_TEST_KEY=... python tools/fulfil.py --poll [--link plink_...] [--dir stock]   # default link: plink_1UZhjiAEYFnTYpgAkqQ7MbPE

   It lists completed Checkout Sessions via the Stripe API, reads `custom_fields` `buyer_name`, runs `claim` on the next RESERVED stock serial, and appends `session -> serial` to `stock/fulfilled.jsonl`. It is idempotent on session id, refuses live-mode sessions and live keys, and needs no Lean run (stock lemmas were checked when minted).
3. A later webhook endpoint must verify the `Stripe-Signature` header before calling `tools/fulfil.py` `fulfil()` (events carry the name in `metadata.buyer_name`).
4. Send the buyer `stock/<serial>.pdf` and `python -m buyatheorem verify <serial> --dir stock`.

## Local tests (no network)
    python tools/fulfil.py tests/fixtures/checkout_completed.json --dir stock

Exit codes: 0 fulfilled, 2 bad event, 3 already fulfilled, 4 stock empty.
