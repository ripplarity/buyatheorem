"""Deterministic lemma families. Each yields Candidate(family, statement, proofs) from (seed, buyer)."""

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    family: str
    statement: str  # Lean Prop text
    proofs: tuple  # tactic blocks to try, in order


class Rng:
    def __init__(self, material: str):
        self.state = hashlib.sha256(material.encode("utf-8")).digest()

    def next(self, lo: int, hi: int) -> int:
        self.state = hashlib.sha256(self.state).digest()
        return lo + int.from_bytes(self.state[:8], "big") % (hi - lo + 1)


def f1(r: Rng) -> Candidate:
    n, a, b = r.next(7, 997), r.next(2, 9999), r.next(2, 9999)
    c = (a * b) % n
    return Candidate("F1", f"({a} * {b}) % {n} = {c}", ("norm_num", "decide", "rfl"))


def f2(r: Rng) -> Candidate:
    k = r.next(3, 60)
    if r.next(0, 1):
        return Candidate("F2", f"∑ i ∈ Finset.range {k}, (2 * i + 1) = {k} ^ 2",
                         ("decide", "simp [Finset.sum_range_succ]", "norm_num [Finset.sum_range_succ]"))
    m = r.next(2, 5)
    v = sum(i ** m for i in range(k))
    return Candidate("F2", f"∑ i ∈ Finset.range {k}, i ^ {m} = {v}",
                     ("decide", "simp [Finset.sum_range_succ]", "norm_num [Finset.sum_range_succ]"))


def f3(r: Rng) -> Candidate:
    a, b = r.next(2, 500), r.next(2, 500)
    return Candidate("F3", f"{a} ^ 2 + {b} ^ 2 ≥ 2 * {a} * {b}",
                     ("norm_num", "nlinarith [sq_nonneg ((" + str(a) + " : ℤ) - " + str(b) + ")]", "decide"))


def f4(r: Rng) -> Candidate:
    n = r.next(8, 30)
    k = r.next(2, n - 2)
    from math import comb
    return Candidate("F4", f"Nat.choose {n} {k} = {comb(n, k)}",
                     ("decide", "norm_num [Nat.choose]", "simp [Nat.choose]", "rfl"))


def f5(r: Rng) -> Candidate:
    """Personal: all parameters come from the buyer-name hash only (seed ignored by caller)."""
    a, b, n = r.next(11, 9999), r.next(11, 9999), r.next(5, 400)
    c = (a * a + b * b) % n
    return Candidate("F5", f"({a} ^ 2 + {b} ^ 2) % {n} = {c}", ("norm_num", "decide", "rfl"))


FAMILIES = {"F1": f1, "F2": f2, "F3": f3, "F4": f4, "F5": f5}
ORDER = ["F1", "F2", "F3", "F4", "F5"]


def candidate(family: str, seed: str, buyer: str, salt: int = 0) -> Candidate:
    if family == "F5":
        material = f"F5|{buyer.strip().casefold()}|{salt}"
    else:
        material = f"{family}|{seed}|{salt}"
    return FAMILIES[family](Rng(material))


def family_order(seed: str) -> list:
    """Rotate start family by seed so seeds spread over families; fall through on failure."""
    s = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % len(ORDER)
    return ORDER[s:] + ORDER[:s]


_FALLBACK = "A small arithmetic fact, checked by Lean 4 + Mathlib."
_NUM = r"(\d+)"
_PATTERNS = {
    "F1": (r"^\(" + _NUM + r" \* " + _NUM + r"\) % " + _NUM + r" = " + _NUM + "$",
           lambda a, b, n, c: f"Multiplying {a} by {b} and dividing the product by {n} leaves remainder {c}."),
    "F5": (r"^\(" + _NUM + r" \^ 2 \+ " + _NUM + r" \^ 2\) % " + _NUM + r" = " + _NUM + "$",
           lambda a, b, n, c: f"Adding the squares of {a} and {b} and dividing by {n} leaves remainder {c}."),
    "F3": (r"^" + _NUM + r" \^ 2 \+ " + _NUM + r" \^ 2 (?:≥|>=) 2 \* " + _NUM + r" \* " + _NUM + "$",
           lambda a, b, c, d: f"The sum of the squares of {a} and {b} is at least twice their product."),
    "F4": (r"^Nat\.choose " + _NUM + " " + _NUM + " = " + _NUM + "$",
           lambda n, k, v: f"There are exactly {v} ways to choose {k} items from {n}."),
}
_F2_ODD = r"^∑ i ∈ Finset\.range " + _NUM + r", \(2 \* i \+ 1\) = " + _NUM + r" \^ 2$"
_F2_POW = r"^∑ i ∈ Finset\.range " + _NUM + r", i \^ " + _NUM + " = " + _NUM + "$"


def describe(family: str, statement: str) -> str:
    """Deterministic one-sentence English reading of a minted statement (no LLM). Uses only family + statement."""
    import re
    try:
        s = " ".join(str(statement).split())
        if family == "F2":
            m = re.match(_F2_ODD, s)
            if m and m.group(1) == m.group(2):
                k = int(m.group(1))
                return f"Adding the first {k} odd numbers gives {k * k}, which is {k} squared."
            m = re.match(_F2_POW, s)
            if m:
                k, p, v = m.groups()
                return f"Adding i to the power {p} for every whole number i from 0 to {int(k) - 1} gives {v}."
        elif family in _PATTERNS:
            pat, fn = _PATTERNS[family]
            m = re.match(pat, s)
            if m:
                return fn(*m.groups())
    except (ValueError, TypeError):
        pass
    return _FALLBACK
