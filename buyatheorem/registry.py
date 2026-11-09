"""Append-only JSONL registry + DSSE attestation (attest-spec v1 pattern, as in sovkit/attest.py)."""

import base64
import hashlib
import json
import os
import platform
import subprocess
import sys
import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from buyatheorem import __version__

PAYLOAD_TYPE = "application/vnd.in-toto+json"
PREDICATE_TYPE = "https://ripplarity.com/attestation/buyatheorem/lemma/v1"
MAX_INT = 2**53 - 1
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFIER = os.path.join(ROOT, "tools", "attest_verify.py")


def registry_dir() -> str:
    d = os.environ.get("BAT_REGISTRY", os.path.join(ROOT, "registry"))
    os.makedirs(d, exist_ok=True)
    return d


def jcs(o) -> bytes:
    return _jcs(o).encode("utf-8")


def _jcs(o) -> str:
    if o is None:
        return "null"
    if o is True:
        return "true"
    if o is False:
        return "false"
    if isinstance(o, int):
        if abs(o) > MAX_INT:
            raise ValueError("integer outside +-(2^53-1)")
        return str(o)
    if isinstance(o, str):
        return json.dumps(o, ensure_ascii=False)
    if isinstance(o, list):
        return "[" + ",".join(_jcs(v) for v in o) + "]"
    if isinstance(o, dict):
        keys = sorted(o, key=lambda k: k.encode("utf-16-be"))
        return "{" + ",".join(_jcs(k) + ":" + _jcs(o[k]) for k in keys) + "}"
    raise ValueError(f"unsupported type {type(o).__name__}")


def pae(t: str, payload: bytes) -> bytes:
    tb = t.encode("utf-8")
    return b"DSSEv1 %d %s %d %s" % (len(tb), tb, len(payload), payload)


def sha256_file(p: str) -> str:
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_key() -> Ed25519PrivateKey:
    kd = os.environ.get("BAT_KEYDIR", os.path.join(ROOT, ".keys"))
    os.makedirs(kd, exist_ok=True)
    kp = os.path.join(kd, "registry.ed25519")
    if os.path.exists(kp):
        return Ed25519PrivateKey.from_private_bytes(
            bytes.fromhex(open(kp).read().strip())
        )
    k = Ed25519PrivateKey.generate()
    raw = k.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    open(kp, "w").write(raw.hex() + "\n")
    return k


def pub_hex(key) -> str:
    return (
        key.public_key()
        .public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        .hex()
    )


def keyid(key) -> str:
    return hashlib.sha256(bytes.fromhex(pub_hex(key))).hexdigest()


def attest(lean_path: str, cert: dict, out_path: str, started: str) -> None:
    key = load_key()
    stmt = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [
            {
                "name": os.path.basename(lean_path),
                "digest": {"sha256": sha256_file(lean_path)},
            }
        ],
        "predicateType": PREDICATE_TYPE,
        "predicate": {
            "producer": {"tool": "buyatheorem", "version": __version__},
            "started": started,
            "ended": utc(),
            "environment": {"host_os": platform.system().lower(), "run_mode": "REAL"},
            "serial": cert["serial"],
            "statement": cert["statement"],
            "statement_hash": cert["statement_hash"],
            "lean_version": cert["lean_version"],
            "mathlib_rev": cert["mathlib_rev"],
            "check_log_sha256": cert["check_log_sha256"],
        },
    }
    payload = jcs(stmt)
    sig = key.sign(pae(PAYLOAD_TYPE, payload))
    env = {
        "payloadType": PAYLOAD_TYPE,
        "payload": base64.b64encode(payload).decode(),
        "signatures": [{"keyid": keyid(key), "sig": base64.b64encode(sig).decode()}],
    }
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(env, f, indent=2)
        f.write("\n")


def verify_attestation(env_path: str, subjects_dir: str) -> int:
    """Run the copied verifier. rc 0 or 5 (unknown predicateType, signature valid) accepted."""
    key = load_key()
    p = subprocess.run(
        [
            sys.executable,
            "-I",
            VERIFIER,
            env_path,
            "--key",
            pub_hex(key),
            "--expect-keyid",
            keyid(key),
            "--check-subjects",
            subjects_dir,
        ],
        capture_output=True,
        text=True,
    )
    return p.returncode


def append(entry: dict, reg: str) -> None:
    p = os.path.join(reg, "registry.jsonl")
    if os.path.exists(p):
        for l in open(p, encoding="utf-8"):
            if l.strip() and json.loads(l)["stmt_hash"] == entry["stmt_hash"]:
                raise ValueError("duplicate statement hash")
    with open(p, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
