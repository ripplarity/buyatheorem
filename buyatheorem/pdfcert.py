"""Certificate PDF via reportlab (pure Python). Bundled Bitstream Vera TTF is embedded (subset)."""

import os

import reportlab

from buyatheorem import certificate
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

_FOLD = {"∑": "sum", "≥": ">=", "≤": "<=", "∈": "in", "≠": "!=", "ℕ": "Nat", "ℤ": "Int"}
HONESTY = "A new, small, checked lemma with your name on it"
PRECEDENT = "Precedent: TheoryMine (2010)."


def fold(s: str) -> str:
    for k, v in _FOLD.items():
        s = s.replace(k, v)
    return "".join(ch if ord(ch) < 128 or ch.isalpha() else "?" for ch in s)


def _fonts():
    d = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
    for name, f in (("Vera", "Vera.ttf"), ("Vera-B", "VeraBd.ttf"), ("Vera-I", "VeraIt.ttf")):
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, os.path.join(d, f)))


def _wrap(c, text, font, size, width):
    words, line, out = text.split(" "), "", []
    for w in words:
        t = (line + " " + w).strip()
        if c.stringWidth(t, font, size) > width and line:
            out.append(line)
            line = w
        else:
            line = t
    out.append(line)
    return out


def render_pdf(cert: dict, out_path: str) -> None:
    _fonts()
    W, H = A4
    c = canvas.Canvas(out_path, pagesize=A4, invariant=1)
    c.setTitle("Theorem certificate " + cert["serial"])
    c.setStrokeColorRGB(0.2, 0.2, 0.3)
    c.setLineWidth(3)
    c.rect(28, 28, W - 56, H - 56)
    c.setLineWidth(0.8)
    c.rect(36, 36, W - 72, H - 72)
    y = H - 100
    c.setFont("Vera-B", 26)
    c.drawCentredString(W / 2, y, "Theorem Certificate")
    y -= 40
    c.setFont("Vera-I", 12)
    c.drawCentredString(W / 2, y, HONESTY)
    y -= 50
    c.setFont("Vera", 12)
    c.drawCentredString(W / 2, y, "Lemma named for")
    y -= 34
    c.setFont("Vera-B", 22)
    c.drawCentredString(W / 2, y, fold(cert["buyer"]))
    y -= 40
    c.setFont("Vera", 11)
    c.drawCentredString(W / 2, y, "Serial: " + cert["serial"])
    y -= 36
    c.setFont("Vera-B", 11)
    c.drawString(60, y, "Lean 4 source")
    y -= 18
    c.setFont("Courier", 9)
    for ln in fold(cert["lean_source"]).splitlines():
        if ln.strip():
            for part in _wrap(c, ln, "Courier", 9, W - 120):
                c.drawString(60, y, part)
                y -= 12
    y -= 6
    c.setFont("Vera-B", 10)
    c.drawString(60, y, "In plain English:")
    y -= 14
    c.setFont("Vera", 10)
    for part in _wrap(c, fold(certificate.plain_english(cert)), "Vera", 10, W - 120):
        c.drawString(60, y, part)
        y -= 13
    y -= 12
    rows = [("Pin", certificate.pin_text(cert)), ("Mathlib commit (full hash)", cert["mathlib_rev"]),
            ("Proof (Lean file) sha256", cert["lean_sha256"]),
            ("Check log sha256", cert["check_log_sha256"] + (" (empty log: Lean printed no messages)" if cert["check_log_sha256"] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" else "")),
            ("Verify (signature only)", f"python tools/attest_verify.py {cert['serial']}.dsse.json --key <pubkey> --expect-keyid <keyid>"),
            ("Verify (full)", f"python -m buyatheorem verify {cert['serial']} (needs a local Lean 4 + Mathlib project; see README)")]
    for k, v in rows:
        c.setFont("Vera-B", 9)
        c.drawString(60, y, k)
        y -= 12
        c.setFont("Courier", 8)
        for part in _wrap(c, fold(v), "Courier", 8, W - 120):
            c.drawString(60, y, part)
            y -= 11
        y -= 5
    c.setFont("Vera-I", 8)
    c.drawString(60, 70, "New means: statement text not found verbatim in Mathlib and not previously minted. No mathematical importance is claimed.")
    c.drawString(60, 56, PRECEDENT)
    c.drawString(60, 44, "The buyer or recipient name is PUBLIC in the registry, the Lean file and this PDF.")
    c.showPage()
    c.save()
