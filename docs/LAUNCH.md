# Launch checklist (founder)

Public launch in Stripe TEST-payment mode by 2026-11-26. No live key until you decide.

## Decisions needed
- [ ] Product name and domain (working name: Buy a Theorem).
- [ ] Price: $29 single, $79 printed proof pack is NOT on sale until print fulfilment exists.
- [ ] Live Stripe key (founder-held; set only in the server environment, never in the repo).
- [ ] Signing key custody and the pinned keyid published on the landing page (`.keys/registry.ed25519` is gitignored; back it up offline).
- [ ] Register the predicateType in attest-spec KNOWN so the verifier returns rc 0 instead of rc 5.
- [ ] Hosting for `web/` and for the public registry/stock files; refund and name-moderation policy.
- [ ] Launch post text (draft below, founder approves exact text before anything is posted).

## Draft launch post (needs founder approval)
Buy a Theorem: a small, new, Lean-checked lemma with your name on it, plus a signed certificate anyone can re-verify. Small by design. Precedent: TheoryMine (2010); ours is Lean 4 + Mathlib, open registry, CC0 lemma texts.

## Pre-mortem
- Mockery of trivial lemmas ("that is just arithmetic"): lean into it. The page says small by design; the product is the checked proof and the name, not significance. Never claim mathematical importance.
- Load: a purchase never runs Lean (claims draw from pre-minted stock, about seconds). Risk is stock running out: `fulfil.py` exits 4; keep the stock above expected weekly sales and mint more with `stock --n`.
- Refunds: a refund after claim leaves a named lemma in the registry. Policy needed: refund before claim only, or retire the serial with a registry note. Stripe refund events are not handled by `fulfil.py` (it ignores them).
- Name abuse: names appear in a public registry; add a moderation check before claim.
- Prior-art optics: TheoryMine did this first; state it plainly (done on page and README).
- Key loss or leak: attestations cannot be re-signed under a new key without a public note.

## Fulfilment
- Run by the operator with `python tools/fulfil.py --poll [--link plink_...]` (env `STRIPE_TEST_KEY`) until a webhook endpoint exists. Idempotent on session id; log in `stock/fulfilled.jsonl`.

## Terms shown on the page before checkout
- Refund any time before you claim your serial. After claim, the serial is retired with a registry note and the fee is not refundable.
- The buyer's or recipient's name becomes PUBLIC in the registry, the Lean file and the PDF. Gifting requires the recipient's consent.
