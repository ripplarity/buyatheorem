import hashlib
import os
import re
import json


def normalise(stmt: str) -> str:
    return re.sub(r"\s+", "", stmt)


def stmt_hash(stmt: str) -> str:
    return hashlib.sha256(normalise(stmt).encode("utf-8")).hexdigest()


def in_mathlib(stmt: str, mathlib_dir: str) -> bool:
    """True if the whitespace-normalised statement occurs in any Mathlib source file."""
    needle = normalise(stmt)
    for root, _, files in os.walk(mathlib_dir):
        for f in files:
            if f.endswith(".lean"):
                try:
                    txt = open(os.path.join(root, f), encoding="utf-8", errors="ignore").read()
                except OSError:
                    continue
                if needle in re.sub(r"\s+", "", txt):
                    return True
    return False


def previously_minted(stmt: str, registry_dir: str) -> bool:
    p = os.path.join(registry_dir, "registry.jsonl")
    if not os.path.exists(p):
        return False
    h = stmt_hash(stmt)
    return any(json.loads(l)["stmt_hash"] == h for l in open(p, encoding="utf-8") if l.strip())
