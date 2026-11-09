<p align="center">
  <img src="assets/logo.svg" width="112" alt="buyatheorem logo: an end-of-proof mark above a name tag">
</p>

<h1 align="center">Buy a Theorem: a small lemma with your name</h1>

<p align="center">
  <b>A new (not in Mathlib text), small, machine-checked lemma, named after you.</b><br>
  Lean 4 + Mathlib decide it is true; a signed registry entry lets anyone re-check it offline.
</p>

<p align="center">
  <img src="assets/badges.svg" alt="Lean 4 + Mathlib checked · signed registry · lemmas CC0 · code Apache-2.0">
</p>

<p align="center">
  <a href="#quick-start">Quick start</a> · <a href="#what-you-get">What you get</a> · <a href="#honesty">Honesty</a> · <a href="#faq">FAQ</a>
</p>

<p align="center"><code>buyatheorem verify &lt;serial&gt;</code></p>

---

## Why

A theorem with your name on it is a fun, odd gift, and the proof is real: Lean checks it, not a language model. The lemmas are deliberately small. What you get is a checked proof, a name, and a record anyone can verify without trusting us.

## Quick start

```bash
uv venv .venv && uv pip install -e .
export BAT_LEANPROJ=/path/to/a/lean4/project/with/mathlib/built   # required
buyatheorem mint --for "Ada Example" --seed 00ff
buyatheorem verify <serial>
pytest -m "not slow"     # fast tests; `pytest -m slow` runs real Lean checks
```

## What you get

| Item | File |
|---|---|
| The lemma, checked by Lean 4 + Mathlib | `registry/<serial>.lean` |
| A one-page certificate (statement, serial, Lean and Mathlib versions, proof hash, verify command) | `.html` / PDF |
| A signed registry entry (DSSE + in-toto) | `.dsse.json`, appended to `registry/registry.jsonl` |
| The certificate data | `.json` |

Check any entry yourself with the standalone verifier: `python tools/attest_verify.py <serial>.dsse.json --key <registry public key hex> --expect-keyid <pinned keyid> --check-subjects .`

## Honesty

- **"New"** means the whitespace-normalised statement is not in Mathlib's sources and was not minted here before. Nothing more.
- **Small by design:** arithmetic, finite sums, small inequalities, binomial coefficients. They are instances of known facts. No mathematical importance is claimed.
- **The registry is ours.** The attestation proves we signed the entry, not that anyone else recognises the name.
- **Precedent:** TheoryMine (Edinburgh, 2010 onward) sold naming rights to machine-proved theorems with a certificate. What differs here: Lean 4 + Mathlib checking, an open registry, signed attestations and CC0 lemma texts. See [`docs/PRIOR_ART.md`](docs/PRIOR_ART.md).

## Fulfilment

Until a webhook endpoint exists, the operator runs `python tools/fulfil.py --poll` (needs `STRIPE_TEST_KEY` in the environment, test mode only) to claim reserved stock for completed test payments.

## Limits

- `verify` needs a local Lean 4 project with Mathlib built (`BAT_LEANPROJ`). Checking the signature alone needs only `tools/attest_verify.py`.
- Registry signing key (compare against the page and release notes before trusting it): `public_key_hex=a19ce6a30882ec88048ecc8300ebe223a342cd07401d3b1bf6f90248d3e00c1a`, `keyid=19dd0c0959a77c864317b230fdb53aacd32d958b6e84a64e4e0488c60f77797e`.
- The buyer's or recipient's name becomes **public** in the registry, the Lean file and the certificate.

## FAQ

**Is the proof real?** Yes. Lean 4 checks it against Mathlib, and the certificate records the Lean version, Mathlib commit and file hashes.

**Is it important mathematics?** No. It is small on purpose; the value is the checked proof and the name.

**Can I buy one as a gift?** Yes, with the recipient's consent, because their name becomes public.

**What about refunds?** Refunds are given any time before the serial is claimed. After claiming, the serial is retired with a registry note.

---

<p align="center"><sub>Code Apache-2.0 · lemma texts CC0 · Ripplarity Inc.</sub></p>
