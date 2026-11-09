import json

import pytest

from buyatheorem import certificate, families, lean_check, novelty, registry


def test_families_deterministic():
    a = families.candidate("F1", "00ff", "X")
    assert a == families.candidate("F1", "00ff", "X")
    assert a != families.candidate("F1", "00fe", "X")


def test_f5_depends_on_name_not_seed():
    assert families.candidate("F5", "1", "Ada Example") == families.candidate("F5", "2", "ada example")
    assert families.candidate("F5", "1", "Ada Example") != families.candidate("F5", "1", "Bob")


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


def test_pdf_certificate(tmp_path):
    import pypdf
    from buyatheorem import pdfcert
    c = {"serial": "bat-abc123", "buyer": "Ada Example", "lean_source": "theorem x : ∑ i ∈ Finset.range 3, i = 3 := by\n  decide\n",
         "lean_version": "Lean (version 4.35.0)", "mathlib_rev": "56a0", "lean_sha256": "a" * 64,
         "check_log_sha256": "b" * 64}
    p = tmp_path / "c.pdf"
    pdfcert.render_pdf(c, str(p))
    assert p.stat().st_size > 10_000
    txt = pypdf.PdfReader(str(p)).pages[0].extract_text()
    assert "bat-abc123" in txt and "Ada Example" in txt and "TheoryMine (2010)" in txt
    assert "small by design" in txt and "verify bat-abc123" in txt


def _fake_stock(d, serial="bat-aaaaaaaaaaaa"):
    import os
    from buyatheorem import stock as st
    src = f"import Mathlib\n\n-- Buyer: RESERVED\n-- Serial: {serial}\ntheorem x : 1 = 1 := by\n  decide\n"
    lp = os.path.join(d, serial + ".lean")
    open(lp, "w", encoding="utf-8", newline="\n").write(src)
    cert = {"serial": serial, "buyer": "RESERVED", "statement": "1 = 1", "statement_hash": "h", "lean_source": src,
            "lean_sha256": registry.sha256_file(lp), "lean_version": "Lean (version 4.35.0)", "mathlib_rev": "r",
            "check_log_sha256": "c"}
    open(os.path.join(d, serial + ".json"), "w", encoding="utf-8", newline="\n").write(certificate.dumps(cert))
    st._write_index(d, [{"serial": serial, "family": "F1", "statement": "1 = 1", "state": "reserved", "buyer": "RESERVED"}])
    return serial


def test_claim_resigns_without_lean(tmp_path, monkeypatch):
    import pypdf
    from buyatheorem import stock as st
    monkeypatch.setenv("BAT_KEYDIR", str(tmp_path / "k"))
    d = str(tmp_path)
    s = _fake_stock(d)
    monkeypatch.setattr(lean_check, "check", lambda *a, **k: (_ for _ in ()).throw(AssertionError("Lean must not run")))
    cert = st.claim(s, "Ada Example", d)
    assert cert["buyer"] == "Ada Example" and cert["checked_sha256"] != cert["lean_sha256"]
    assert "Ada Example" in pypdf.PdfReader(str(tmp_path / (s + ".pdf"))).pages[0].extract_text()
    assert registry.verify_attestation(str(tmp_path / (s + ".dsse.json")), d) == 5
    assert st.read_index(d)[0]["state"] == "claimed"
    with pytest.raises(ValueError):
        st.claim(s, "Other", d)


def test_claim_unknown_serial(tmp_path):
    from buyatheorem import stock as st
    _fake_stock(str(tmp_path))
    with pytest.raises(KeyError):
        st.claim("bat-nope", "X", str(tmp_path))


def test_next_reserved(tmp_path):
    from buyatheorem import stock as st
    s = _fake_stock(str(tmp_path))
    assert st.next_reserved(str(tmp_path)) == s


def test_leanproj_required(monkeypatch):
    monkeypatch.delenv("BAT_LEANPROJ", raising=False)
    with pytest.raises(RuntimeError, match="set BAT_LEANPROJ"):
        lean_check.leanproj()
