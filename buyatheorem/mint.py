import json
import os
import re

from buyatheorem import certificate, families, lean_check, novelty, pdfcert, registry


def clean_buyer(b: str) -> str:
    b = re.sub(r"[^\w .,'\-]", "", b, flags=re.UNICODE).strip()
    if not b:
        raise ValueError("empty buyer name")
    return b[:80]


def lean_source(serial_id: str, buyer: str, stmt: str, tactic: str) -> str:
    return (
        f"import Mathlib\n\n-- Buyer: {buyer}\n-- Serial: {serial_id}\n"
        f"theorem {serial_id.replace('-', '_')} : {stmt} := by\n  {tactic}\n"
    )


def mint(buyer: str, seed: str, log=print, skip_mathlib_grep: bool = False) -> dict:
    buyer = clean_buyer(buyer)
    reg = registry.registry_dir()
    started = registry.utc()
    for fam in families.family_order(seed):
        for salt in range(3):
            c = families.candidate(fam, seed, buyer, salt)
            h = novelty.stmt_hash(c.statement)
            if novelty.previously_minted(c.statement, reg):
                log(f"{fam}/{salt}: already minted, next")
                continue
            if not skip_mathlib_grep and novelty.in_mathlib(
                c.statement, lean_check.mathlib_src()
            ):
                log(f"{fam}/{salt}: statement text found in Mathlib, next")
                continue
            serial = "bat-" + h[:12]
            lean_path = os.path.join(reg, serial + ".lean")
            for tac in c.proofs:
                with open(lean_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(lean_source(serial, buyer, c.statement, tac))
                ok, lg = lean_check.check(lean_path)
                log(f"{fam}/{salt} tactic '{tac}': {'OK' if ok else 'FAIL'}")
                if ok:
                    src = open(lean_path, encoding="utf-8").read()
                    cert = {
                        "serial": serial,
                        "buyer": buyer,
                        "family": fam,
                        "tactic": tac,
                        "seed": seed,
                        "statement": c.statement,
                        "statement_hash": h,
                        "lean_source": src,
                        "lean_sha256": registry.sha256_file(lean_path),
                        "lean_version": lean_check.lean_version(),
                        "mathlib_rev": lean_check.mathlib_rev(),
                        "check_log_sha256": lean_check.log_hash(lg),
                        "minted_at": registry.utc(),
                    }
                    with open(
                        os.path.join(reg, serial + ".json"),
                        "w",
                        encoding="utf-8",
                        newline="\n",
                    ) as f:
                        f.write(certificate.dumps(cert))
                    with open(
                        os.path.join(reg, serial + ".html"),
                        "w",
                        encoding="utf-8",
                        newline="\n",
                    ) as f:
                        f.write(certificate.render_html(cert))
                    pdfcert.render_pdf(cert, os.path.join(reg, serial + ".pdf"))
                    registry.attest(
                        lean_path,
                        cert,
                        os.path.join(reg, serial + ".dsse.json"),
                        started,
                    )
                    registry.append(
                        {
                            "serial": serial,
                            "stmt_hash": h,
                            "lean_sha256": cert["lean_sha256"],
                            "buyer": buyer,
                            "minted_at": cert["minted_at"],
                        },
                        reg,
                    )
                    return cert
            if os.path.exists(lean_path):
                os.remove(lean_path)
    raise RuntimeError("no family produced a checkable lemma")


def verify(serial: str, log=print) -> int:
    reg = registry.registry_dir()
    lp, jp, ep = (
        os.path.join(reg, serial + e) for e in (".lean", ".json", ".dsse.json")
    )
    cert = json.load(open(jp, encoding="utf-8"))
    if registry.sha256_file(lp) != cert["lean_sha256"]:
        log("FAIL: lean file hash differs from certificate")
        return 1
    rc = registry.verify_attestation(ep, reg)
    if rc not in (0, 5):
        log(f"FAIL: attestation rc {rc}")
        return 1
    ok, _ = lean_check.check(lp)
    if not ok:
        log("FAIL: Lean check failed")
        return 1
    log(f"OK {serial} (attestation rc {rc})")
    return 0
