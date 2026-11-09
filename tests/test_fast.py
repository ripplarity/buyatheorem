import os
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


@pytest.mark.skipif(not os.environ.get("BAT_LEANPROJ"), reason="needs BAT_LEANPROJ")
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
    flat = txt.replace(chr(10), " ")
    assert "A new, small, checked lemma with your name on it" in flat and "attest_verify.py bat-abc123.dsse.json" in flat
    assert flat.index("attest_verify.py") < flat.index("buyatheorem verify bat-abc123") and "see README" in flat


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


def test_cli_survives_cp1252_stdout():
    import subprocess
    import sys
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    r = subprocess.run([sys.executable, "-c", "import buyatheorem.cli; print('\u2124 \u2211')"],
                       capture_output=True, env=env)
    assert r.returncode == 0 and "ℤ".encode("utf-8") in r.stdout


def _env(tmp_path, monkeypatch, lean_ok):
    monkeypatch.setenv("BAT_REGISTRY", str(tmp_path / "reg"))
    monkeypatch.setenv("BAT_KEYDIR", str(tmp_path / "k"))
    monkeypatch.setattr(lean_check, "check", lambda *a, **k: (lean_ok, "ok"))
    monkeypatch.setattr(lean_check, "lean_version", lambda: "Lean (version 4.35.0)")
    monkeypatch.setattr(lean_check, "mathlib_rev", lambda: "r")


def test_mint_failure_leaves_registry_empty(tmp_path, monkeypatch):
    from buyatheorem import mint as m
    _env(tmp_path, monkeypatch, False)
    with pytest.raises(RuntimeError):
        m.mint("Ada Example", "0abc", skip_mathlib_grep=True)
    assert os.listdir(tmp_path / "reg") == []


def test_mint_registry_failure_rolls_back(tmp_path, monkeypatch):
    from buyatheorem import mint as m
    _env(tmp_path, monkeypatch, True)
    monkeypatch.setattr(registry, "append", lambda *a, **k: (_ for _ in ()).throw(ValueError("dup")))
    with pytest.raises(ValueError):
        m.mint("Ada Example", "0abc", skip_mathlib_grep=True)
    assert os.listdir(tmp_path / "reg") == []


def test_mint_success_lands_all_files(tmp_path, monkeypatch):
    from buyatheorem import mint as m
    _env(tmp_path, monkeypatch, True)
    cert = m.mint("Ada Example", "0abc", skip_mathlib_grep=True)
    names = set(os.listdir(tmp_path / "reg"))
    assert {cert["serial"] + e for e in (".lean", ".json", ".html", ".pdf", ".dsse.json")} <= names
    assert not any(n.startswith(".mint-") for n in names)


def test_page_has_refund_public_name_and_no_79_sale():
    page = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    assert "Refund any time before you claim your serial. After claim, the serial is retired with a registry note and the fee is not refundable." in page
    assert "name becomes PUBLIC in the registry, the Lean file and the PDF" in page
    assert "Gifting requires the recipient's consent" in page
    assert "Not on sale yet" in page and "a new, small, checked lemma" in page.lower()


def test_empty_log_label_in_html_and_pdf(tmp_path):
    import pypdf
    from buyatheorem import pdfcert
    c = {"serial": "bat-e", "buyer": "Ada Example", "lean_source": "x", "lean_version": "v", "mathlib_rev": "r",
         "lean_sha256": "a" * 64, "check_log_sha256": certificate.EMPTY}
    assert "empty log: Lean printed no messages" in certificate.render_html(c)
    pdfcert.render_pdf(c, str(tmp_path / "e.pdf"))
    txt = pypdf.PdfReader(str(tmp_path / "e.pdf")).pages[0].extract_text().replace(chr(10), " ")
    assert "empty log" in txt and "PUBLIC" in txt


def test_reset_restores_reserved_and_ship_check(tmp_path, monkeypatch):
    import pypdf
    from buyatheorem import stock as st
    monkeypatch.setenv("BAT_KEYDIR", str(tmp_path / "k"))
    d = str(tmp_path)
    s = _fake_stock(d)
    assert st.ship_check(d) == 1
    orig = open(os.path.join(d, s + ".lean"), encoding="utf-8").read()
    st.claim(s, "Ada Example", d)
    with pytest.raises(st.ClaimedInStock):
        st.ship_check(d)
    st.reset(s, d)
    assert open(os.path.join(d, s + ".lean"), encoding="utf-8").read() == orig
    assert st.read_index(d)[0]["state"] == "reserved" and st.ship_check(d) == 1
    txt = pypdf.PdfReader(os.path.join(d, s + ".pdf")).pages[0].extract_text()
    assert "Ada Example" not in txt and "RESERVED" in txt
    assert registry.verify_attestation(os.path.join(d, s + ".dsse.json"), d) == 5
    st.claim(s, "Next Buyer", d)


def _fake_run(rc, out=""):
    import subprocess

    def run(*a, **k):
        return subprocess.CompletedProcess(a, rc, stdout=out, stderr="")
    return run


@pytest.mark.parametrize("rc,out", [(137, ""), (-9, ""), (1, ""), (1, None)])
def test_lean_error_classification(tmp_path, monkeypatch, rc, out):
    monkeypatch.setenv("BAT_LEANPROJ", str(tmp_path))
    monkeypatch.setattr(lean_check.subprocess, "run", _fake_run(rc, out))
    with pytest.raises(lean_check.LeanError):
        lean_check.check(str(tmp_path / "x.lean"))


def test_tactic_failure_is_not_lean_error(tmp_path, monkeypatch):
    monkeypatch.setenv("BAT_LEANPROJ", str(tmp_path))
    monkeypatch.setattr(lean_check.subprocess, "run", _fake_run(1, "x.lean:3:2: error: linarith failed"))
    assert lean_check.check(str(tmp_path / "x.lean"))[0] is False


def test_timeout_is_lean_error(tmp_path, monkeypatch):
    import subprocess
    monkeypatch.setenv("BAT_LEANPROJ", str(tmp_path))

    def boom(*a, **k):
        raise subprocess.TimeoutExpired("lake", 1)
    monkeypatch.setattr(lean_check.subprocess, "run", boom)
    with pytest.raises(lean_check.LeanError):
        lean_check.check(str(tmp_path / "x.lean"), timeout=1)


def test_cli_mint_lean_error_exits_3(tmp_path, monkeypatch):
    from typer.testing import CliRunner
    from buyatheorem import cli
    monkeypatch.setenv("BAT_REGISTRY", str(tmp_path / "reg"))
    monkeypatch.setenv("BAT_KEYDIR", str(tmp_path / "k"))
    monkeypatch.setenv("BAT_LEANPROJ", str(tmp_path))
    monkeypatch.setattr(novelty, "in_mathlib", lambda *x, **k: False)
    calls = []

    def killed(*a, **k):
        calls.append(1)
        raise lean_check.LeanError("lean process killed (rc 137)")
    monkeypatch.setattr(lean_check, "check", killed)
    r = CliRunner().invoke(cli.app, ["mint", "--for", "Ada Example", "--seed", "0abc"])
    assert r.exit_code == 3 and "LEAN-ERROR: lean process killed (rc 137)" in r.output
    assert len(calls) == 1 and os.listdir(tmp_path / "reg") == []
