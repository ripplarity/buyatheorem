import json

from jinja2 import Template

HTML = Template(
    """<!doctype html><meta charset="utf-8"><title>Theorem certificate {{ c.serial }}</title>
<style>body{font-family:Georgia,serif;max-width:40em;margin:3em auto;border:3px double #444;padding:2em}
code,pre{background:#f4f4f4;padding:.2em}</style>
<h1>Theorem Certificate</h1>
<p>A new, machine-checked lemma named for <b>{{ c.buyer }}</b>.</p>
<p>Serial: <code>{{ c.serial }}</code></p>
<pre>{{ c.lean_source }}</pre>
<p>Checked with {{ c.lean_version }}; Mathlib {{ c.mathlib_rev }}.<br>
Lean file sha256: <code>{{ c.lean_sha256 }}</code><br>Check log sha256: <code>{{ c.check_log_sha256 }}</code>{% if c.check_log_sha256 == EMPTY %} (empty log: Lean printed no messages){% endif %}</p>
<p><i>New means not found verbatim in Mathlib and not previously minted. The lemma is small; the value is the checked proof and the name. No mathematical importance is claimed.</i></p>""",
    autoescape=True,
)


EMPTY = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def render_html(c: dict) -> str:
    return HTML.render(c=c, EMPTY=EMPTY)


def dumps(c: dict) -> str:
    return json.dumps(c, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
