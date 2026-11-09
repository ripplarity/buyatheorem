import json
import os
import re
import shutil
import tempfile

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


def _mint(tmp: str, 
    buyer: str,
    seed: str,
    log=print,
    skip_mathlib_grep: bool = False,
    first_family: str = None,
    derive_name: str = None,
) -> dict:
    buyer = clean_buyer(buyer)
    reg = registry.registry_dir()
    started = registry.utc()
    order = families.family_order(seed)
    if first_family:
        order = [first_family] + [f for f in order if f != first_family]
    for fam in order:
        for salt in range(3):
            c = families.candidate(fam, seed, derive_name or buyer, salt)
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
            lean_path = os.path.join(tmp, serial + ".lean")
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
                        os.path.join(tmp, serial + ".json"),
                        "w",
                        encoding="utf-8",
                        newline="\n",
                    ) as f:
                        f.write(certificate.dumps(cert))
                    with open(
                        os.path.join(tmp, serial + ".html"),
                        "w",
                        encoding="utf-8",
                        newline="\n",
                    ) as f:
                        f.write(certificate.render_html(cert))
                    pdfcert.render_pdf(cert, os.path.join(tmp, serial + ".pdf"))
                    registry.attest(
                        lean_path,
                        cert,
                        os.path.join(tmp, serial + ".dsse.json"),
                        started,
                    )
                    return cert
    raise RuntimeError("no family produced a checkable lemma")


def mint(buyer: str, seed: str, **kw) -> dict:
    """Atomic: everything is built in a temp dir inside the registry; files land only after Lean passes."""
    reg = registry.registry_dir()
    tmp = tempfile.mkdtemp(prefix=".mint-", dir=reg)
    moved = []
    try:
        cert = _mint(tmp, buyer, seed, **kw)
        try:
            for name in sorted(os.listdir(tmp)):
                os.replace(os.path.join(tmp, name), os.path.join(reg, name))
                moved.append(name)
            registry.append(
                {"serial": cert["serial"], "stmt_hash": cert["statement_hash"],
                 "lean_sha256": cert["lean_sha256"], "buyer": cert["buyer"], "minted_at": cert["minted_at"]},
                reg,
            )
        except Exception:
            for name in moved:
                try:
                    os.remove(os.path.join(reg, name))
                except OSError:
                    pass
            raise
        return cert
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


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
    try:
        ok, _ = lean_check.check(lp)
    except lean_check.LeanError as e:
        log(f"FAIL: LEAN-ERROR: {e}")
        return 1
    if not ok:
        log("FAIL: Lean check failed")
        return 1
    log(f"OK {serial} (attestation rc {rc})")
    return 0
