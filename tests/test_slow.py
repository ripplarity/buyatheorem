import os
import subprocess
import sys

import pytest
from buyatheorem import families, lean_check, mint
from buyatheorem.mint import lean_source

pytestmark = pytest.mark.slow
SEEDS = ["00ff", "a1b2", "deadbeef"]


@pytest.mark.parametrize("fam", families.ORDER)
def test_family_checks_in_lean(fam, tmp_path):
    for seed in SEEDS:
        c = families.candidate(fam, seed, "Test Person")
        ok = False
        for tac in c.proofs:
            p = tmp_path / f"{fam}_{seed}.lean"
            p.write_text(
                lean_source("bat_t", "Test Person", c.statement, tac),
                encoding="utf-8",
                newline="\n",
            )
            ok, log = lean_check.check(str(p))
            if ok:
                break
        assert ok, (fam, seed, c.statement, log[:300])


def test_lean_version_line():
    assert lean_check.lean_version().startswith("Lean (version 4.")


def test_false_statement_fails(tmp_path):
    p = tmp_path / "bad.lean"
    p.write_text(
        "import Mathlib\ntheorem bad : (2 * 3) % 5 = 2 := by norm_num\n", newline="\n"
    )
    assert lean_check.check(str(p))[0] is False


def test_mint_verify_tamper(tmp_path, monkeypatch):
    monkeypatch.setenv("BAT_REGISTRY", str(tmp_path / "reg"))
    monkeypatch.setenv("BAT_KEYDIR", str(tmp_path / "k"))
    cert = mint.mint("Test Person", "00ff", skip_mathlib_grep=True)
    s = cert["serial"]
    assert mint.verify(s) == 0
    # duplicate buyer+seed must produce a different lemma, not a repeat
    cert2 = mint.mint("Test Person", "00ff", skip_mathlib_grep=True)
    assert cert2["serial"] != s
    lp = tmp_path / "reg" / (s + ".lean")
    lp.write_text(
        lp.read_text(encoding="utf-8").replace("by", "bx", 1),
        encoding="utf-8",
        newline="\n",
    )
    assert mint.verify(s) != 0


def test_cli_mint_cp1252_pipe(tmp_path):
    env = dict(os.environ, PYTHONIOENCODING="cp1252", BAT_REGISTRY=str(tmp_path / "reg"), BAT_KEYDIR=str(tmp_path / "k"))
    r = subprocess.run([sys.executable, "-m", "buyatheorem", "mint", "--for", "Ada Example", "--seed", "0abc"],
                       capture_output=True, env=env)
    assert r.returncode == 0, r.stderr[-300:]
    serial = r.stdout.decode("utf-8").split()[-1]
    for ext in (".lean", ".json", ".html", ".dsse.json"):
        assert (tmp_path / "reg" / (serial + ext)).exists()
