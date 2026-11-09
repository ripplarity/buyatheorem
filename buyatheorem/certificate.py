import json
import re

from jinja2 import Template

HTML = Template(
    """<!doctype html><meta charset="utf-8"><title>Theorem certificate {{ c.serial }}</title>
<style>body{font-family:Georgia,serif;max-width:40em;margin:3em auto;border:3px double #444;padding:2em}
code,pre{background:#f4f4f4;padding:.2em}</style>
<h1>Theorem Certificate</h1>
<p>A new, machine-checked lemma named for <b>{{ c.buyer }}</b>.</p>
<p>Serial: <code>{{ c.serial }}</code></p>
<pre>{{ c.lean_source }}</pre>
<p><b>In plain English:</b> {{ plain }}</p>
<p>Checked with {{ pin }}.<br>Mathlib commit (full hash): {% if c.mathlib_rev|length == 40 %}<a href="https://github.com/leanprover-community/mathlib4/commit/{{ c.mathlib_rev }}"><code>{{ c.mathlib_rev }}</code></a>{% else %}<code>{{ c.mathlib_rev }}</code>{% endif %}<br>
Lean file sha256: <code>{{ c.lean_sha256 }}</code><br>Check log sha256: <code>{{ c.check_log_sha256 }}</code>{% if c.check_log_sha256 == EMPTY %} (empty log: Lean printed no messages){% endif %}</p>
<p><i>New means not found verbatim in Mathlib and not previously minted. The lemma is small; the value is the checked proof and the name. No mathematical importance is claimed.</i></p>""",
    autoescape=True,
)


EMPTY = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def plain_english(c: dict) -> str:
    from buyatheorem import families
    return families.describe(c.get("family", ""), c.get("statement", ""))


def pin_text(c: dict) -> str:
    """Lean 4.x.y, Mathlib commit <first 12 hex> (full hash below)."""
    m = re.search(r"version (\d+\.\d+\.\d+)", c.get("lean_version", ""))
    lean = "Lean " + m.group(1) if m else c.get("lean_version", "Lean 4")
    return f"{lean}, Mathlib commit {c.get('mathlib_rev', '')[:12]} (full hash below)"


def render_html(c: dict) -> str:
    return HTML.render(c=c, EMPTY=EMPTY, plain=plain_english(c), pin=pin_text(c))


def dumps(c: dict) -> str:
    return json.dumps(c, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
