import hashlib
import os
import subprocess


def leanproj() -> str:
    p = os.environ.get("BAT_LEANPROJ")
    if not p:
        raise RuntimeError("set BAT_LEANPROJ to a Lean 4 project with Mathlib built")
    return p


def lean_version() -> str:
    p = subprocess.run(
        ["lake", "env", "lean", "--version"],
        cwd=leanproj(),
        capture_output=True,
        text=True,
        timeout=300,
    )
    return p.stdout.strip()


def mathlib_rev() -> str:
    import json

    m = json.load(open(os.path.join(leanproj(), "lake-manifest.json"), encoding="utf-8"))
    for p in m["packages"]:
        if p["name"] == "mathlib":
            return p["rev"]
    return "unknown"


def mathlib_src() -> str:
    return os.path.join(leanproj(), ".lake", "packages", "mathlib", "Mathlib")


def check(path: str, timeout: int = 600):
    """Return (ok, log_text). ok only if rc 0, no 'sorry' warning, no error."""
    try:
        p = subprocess.run(
            ["lake", "env", "lean", os.path.abspath(path)],
            cwd=leanproj(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    log = (p.stdout or "") + (p.stderr or "")
    ok = p.returncode == 0 and "sorry" not in log and "error" not in log
    return ok, log


def log_hash(log: str) -> str:
    return hashlib.sha256(log.encode("utf-8")).hexdigest()
