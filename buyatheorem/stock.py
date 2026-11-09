"""Pre-minted stock: Lean-checked lemmas minted for 'RESERVED', claimed later without re-running Lean."""

import json
import os
import time

from buyatheorem import certificate, mint as m, pdfcert, registry
from buyatheorem.families import ORDER

RESERVED = "RESERVED"


def _index_path(d):
    return os.path.join(d, "index.jsonl")


def read_index(d):
    p = _index_path(d)
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def _write_index(d, rows):
    p = _index_path(d)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    os.replace(tmp, p)


def stock(n: int, out: str, log=print) -> list:
    """Mint until the index has n rows. Resumable: each lemma is indexed as soon as it is checked."""
    os.makedirs(out, exist_ok=True)
    os.environ["BAT_REGISTRY"] = out
    rows = read_index(out)
    i = len(rows)
    while i < n:
        fam = ORDER[i % len(ORDER)]
        t0 = time.time()
        cert = m.mint(RESERVED, f"stock{i:05d}", log=log, first_family=fam, derive_name=f"{RESERVED}-{i}")
        rows.append({"serial": cert["serial"], "family": cert["family"], "statement": cert["statement"],
                     "state": "reserved", "buyer": RESERVED, "secs": round(time.time() - t0, 1)})
        _write_index(out, rows)
        log(f"stock {i + 1}/{n} {cert['serial']} {cert['family']} {rows[-1]['secs']}s")
        i += 1
    return rows


def claim(serial: str, name: str, d: str) -> dict:
    """Re-sign a reserved certificate for a buyer. No Lean run: the Lean check is already recorded."""
    name = m.clean_buyer(name)
    rows = read_index(d)
    row = next((r for r in rows if r["serial"] == serial), None)
    if row is None:
        raise KeyError("unknown serial")
    if row["state"] != "reserved":
        raise ValueError("serial already claimed")
    os.environ["BAT_REGISTRY"] = d
    lp, jp = os.path.join(d, serial + ".lean"), os.path.join(d, serial + ".json")
    cert = json.load(open(jp, encoding="utf-8"))
    src = open(lp, encoding="utf-8").read()
    old = f"-- Buyer: {RESERVED}\n"
    if old not in src:
        raise ValueError("lean file is not a reserved lemma")
    cert["checked_sha256"] = cert["lean_sha256"]  # hash of the exact file Lean checked (name comment differs only)
    src = src.replace(old, f"-- Buyer: {name}\n", 1)
    with open(lp, "w", encoding="utf-8", newline="\n") as f:
        f.write(src)
    cert.update({"buyer": name, "lean_source": src, "lean_sha256": registry.sha256_file(lp),
                 "claimed_at": registry.utc()})
    with open(jp, "w", encoding="utf-8", newline="\n") as f:
        f.write(certificate.dumps(cert))
    with open(os.path.join(d, serial + ".html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(certificate.render_html(cert))
    pdfcert.render_pdf(cert, os.path.join(d, serial + ".pdf"))
    registry.attest(lp, cert, os.path.join(d, serial + ".dsse.json"), cert["claimed_at"])
    row.update({"state": "claimed", "buyer": name})
    _write_index(d, rows)
    with open(os.path.join(d, "registry.jsonl"), "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"event": "claim", "serial": serial, "stmt_hash": cert["statement_hash"],
                            "lean_sha256": cert["lean_sha256"], "buyer": name, "minted_at": cert["claimed_at"]},
                           sort_keys=True) + "\n")
    return cert


def next_reserved(d: str) -> str:
    for r in read_index(d):
        if r["state"] == "reserved":
            return r["serial"]
    raise LookupError("stock empty")


class ClaimedInStock(Exception):
    pass


def ship_check(d: str) -> int:
    """Refuse to ship a stock dir that contains any claimed row. Returns row count."""
    rows = read_index(d)
    bad = [r["serial"] for r in rows if r["state"] != "reserved" or r.get("buyer") != RESERVED]
    if bad:
        raise ClaimedInStock("claimed rows present: " + ", ".join(bad))
    return len(rows)


def reset(serial: str, d: str) -> None:
    """Undo a claim: restore RESERVED, drop the claimed PDF and rebuild reserved artefacts."""
    rows = read_index(d)
    row = next((r for r in rows if r["serial"] == serial), None)
    if row is None:
        raise KeyError("unknown serial")
    if row["state"] == "reserved":
        return
    os.environ["BAT_REGISTRY"] = d
    lp, jp = os.path.join(d, serial + ".lean"), os.path.join(d, serial + ".json")
    cert = json.load(open(jp, encoding="utf-8"))
    src = open(lp, encoding="utf-8").read()
    src = src.replace(f"-- Buyer: {cert['buyer']}\n", f"-- Buyer: {RESERVED}\n", 1)
    with open(lp, "w", encoding="utf-8", newline="\n") as f:
        f.write(src)
    if registry.sha256_file(lp) != cert["checked_sha256"]:
        raise ValueError("restored file does not match the originally checked hash")
    cert.update({"buyer": RESERVED, "lean_source": src, "lean_sha256": cert.pop("checked_sha256")})
    cert.pop("claimed_at", None)
    with open(jp, "w", encoding="utf-8", newline="\n") as f:
        f.write(certificate.dumps(cert))
    with open(os.path.join(d, serial + ".html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(certificate.render_html(cert))
    pp = os.path.join(d, serial + ".pdf")
    if os.path.exists(pp):
        os.remove(pp)
    pdfcert.render_pdf(cert, pp)
    registry.attest(lp, cert, os.path.join(d, serial + ".dsse.json"), registry.utc())
    row.update({"state": "reserved", "buyer": RESERVED})
    _write_index(d, rows)
    with open(os.path.join(d, "registry.jsonl"), "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"event": "reset", "serial": serial, "stmt_hash": cert["statement_hash"],
                            "lean_sha256": cert["lean_sha256"], "buyer": RESERVED, "minted_at": registry.utc()},
                           sort_keys=True) + "\n")
