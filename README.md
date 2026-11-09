# buyatheorem

Precedent: TheoryMine (Edinburgh, theorymine.co.uk, 2010 onward) sold naming rights to automatically generated, machine-proved theorems with a PDF certificate. buyatheorem is a re-implementation of that idea with different machinery: Lean 4 + Mathlib checking, an open registry anyone can re-verify with the standalone verifier (`tools/attest_verify.py`), signed attestations, and CC0 lemma texts.

    buyatheorem mint --for "Asha R." --seed 00ff
    buyatheorem verify <serial>

Each mint writes `registry/<serial>.lean` (checked by Lean 4 + Mathlib), `.json` (certificate),
`.html` (one-page certificate), `.dsse.json` (signed attestation), and appends to `registry/registry.jsonl`.

Honest framing: "new" means the statement text is not found verbatim in Mathlib and was not minted before.
The lemmas are small (arithmetic, finite sums, small inequalities, binomials). The value is the checked proof
and the name. No mathematical importance is claimed. Lean decides validity; no model does.

Lean/Mathlib are reused from a local project (`BAT_LEANPROJ`, default the portfolio leanproj). Code Apache-2.0, lemma texts CC0.
Tests: `pytest -m "not slow"` and `pytest -m slow` (real Lean checks). See docs/PRIOR_ART.md.
