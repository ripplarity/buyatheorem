import json

import pytest

from buyatheorem import certificate, families, lean_check, novelty, registry


def test_families_deterministic():
    a = families.candidate("F1", "00ff", "X")
    assert a == families.candidate("F1", "00ff", "X")
    assert a != families.candidate("F1", "00fe", "X")


def test_f5_depends_on_name_not_seed():
    assert families.candidate("F5", "1", "Asha R.") == families.candidate("F5", "2", "asha r.")
    assert families.candidate("F5", "1", "Asha R.") != families.candidate("F5", "1", "Bob")


def test_family_order_covers_all():
    assert sorted(families.family_order("abc")) == sorted(families.ORDER)


def test_statement_values_correct():
    c = families.candidate("F4", "s", "x")
    n, k, v = (int(t) for t in c.statement.replace("Nat.choose", "").replace("=", "").split())
    from math import comb
    assert comb(n, k) == v


def test_novelty_normalise():
    assert novelty.stmt_hash("a  +\n b = c") == novelty.stmt_hash("a+b=c")


def test_novelty_rejects_mathlib_text():
    import os
    d = os.path.join(lean_check.mathlib_src(), "Algebra", "Group")
    f = next(os.path.join(d, x) for x in sorted(os.listdir(d)) if x.endswith(".lean"))
    line = next(l.strip() for l in open(f, encoding="utf-8") if len(l.strip()) > 30 and not l.strip().startswith(("--", "/")))
    assert novelty.in_mathlib(line, os.path.join(lean_check.mathlib_src(), "Algebra", "Group"))
    assert not novelty.in_mathlib("(123457 * 98761) % 997 = 424242", os.path.join(lean_check.mathlib_src(), "Algebra", "Group"))


def test_registry_rejects_duplicate(tmp_path):
    e = {"serial": "s", "stmt_hash": "h1"}
    registry.append(e, str(tmp_path))
    with pytest.raises(ValueError):
        registry.append(e, str(tmp_path))
    assert novelty.previously_minted("x", str(tmp_path)) is False


def test_previously_minted(tmp_path):
    registry.append({"serial": "s", "stmt_hash": novelty.stmt_hash("p = q")}, str(tmp_path))
    assert novelty.previously_minted("p  =  q", str(tmp_path))


def test_certificate_renders():
    c = {"serial": "bat-1", "buyer": "<b>Asha</b>", "lean_source": "x", "lean_version": "v",
         "mathlib_rev": "r", "lean_sha256": "a", "check_log_sha256": "b"}
    h = certificate.render_html(c)
    assert "bat-1" in h and "&lt;b&gt;Asha" in h and "importance is claimed" in h
    assert json.loads(certificate.dumps(c))["serial"] == "bat-1"


def test_attestation_signs_and_verifies(tmp_path, monkeypatch):
    monkeypatch.setenv("BAT_KEYDIR", str(tmp_path / "k"))
    lean = tmp_path / "bat-1.lean"
    lean.write_text("x\n", newline="\n")
    cert = {"serial": "bat-1", "statement": "s", "statement_hash": "h", "lean_version": "v",
            "mathlib_rev": "r", "check_log_sha256": "c"}
    registry.attest(str(lean), cert, str(tmp_path / "bat-1.dsse.json"), registry.utc())
    assert registry.verify_attestation(str(tmp_path / "bat-1.dsse.json"), str(tmp_path)) == 5
    lean.write_text("y\n", newline="\n")
    assert registry.verify_attestation(str(tmp_path / "bat-1.dsse.json"), str(tmp_path)) == 3


def test_clean_buyer():
    from buyatheorem.mint import clean_buyer
    assert "\n" not in clean_buyer("A\nB -/ x")
    with pytest.raises(ValueError):
        clean_buyer("!!!")
