import copy
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import fulfil  # noqa: E402
from buyatheorem import stock as st  # noqa: E402
from test_fast import _fake_stock  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "checkout_completed.json")


@pytest.fixture
def ev():
    return json.load(open(FIX, encoding="utf-8"))


def test_fulfil_claims_for_metadata_name(tmp_path, monkeypatch, ev):
    monkeypatch.setenv("BAT_KEYDIR", str(tmp_path / "k"))
    s = _fake_stock(str(tmp_path))
    assert fulfil.fulfil(ev, str(tmp_path)) == s
    assert st.read_index(str(tmp_path))[0]["buyer"] == "Ada Example"


def test_fulfil_idempotent(tmp_path, monkeypatch, ev):
    monkeypatch.setenv("BAT_KEYDIR", str(tmp_path / "k"))
    _fake_stock(str(tmp_path))
    fulfil.fulfil(ev, str(tmp_path))
    with pytest.raises(fulfil.Skip) as e:
        fulfil.fulfil(ev, str(tmp_path))
    assert e.value.rc == 3


def test_fulfil_refuses_live_unpaid_and_nameless(tmp_path, ev):
    _fake_stock(str(tmp_path))
    for mut in (lambda e: e.update(livemode=True), lambda e: e["data"]["object"].update(payment_status="unpaid"),
                lambda e: e["data"]["object"].update(metadata={}), lambda e: e.update(type="charge.refunded")):
        e2 = copy.deepcopy(ev)
        mut(e2)
        with pytest.raises(fulfil.Skip) as x:
            fulfil.fulfil(e2, str(tmp_path))
        assert x.value.rc == 2


def test_fulfil_stock_empty(tmp_path, ev):
    st._write_index(str(tmp_path), [])
    with pytest.raises(fulfil.Skip) as x:
        fulfil.fulfil(ev, str(tmp_path))
    assert x.value.rc == 4


SESS = os.path.join(os.path.dirname(__file__), "fixtures", "sessions_list.json")


def _two_stock(tmp_path):
    d = str(tmp_path)
    _fake_stock(d, "bat-aaaaaaaaaaaa")
    rows = st.read_index(d)
    from test_fast import _fake_stock as fs
    fs(d, "bat-bbbbbbbbbbbb")
    rows += st.read_index(d)
    st._write_index(d, rows)
    return d


def test_poll_claims_paid_test_sessions_in_order_and_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("BAT_KEYDIR", str(tmp_path / "k"))
    d = _two_stock(tmp_path)
    sessions = json.load(open(SESS, encoding="utf-8"))["data"]
    msgs = []
    assert fulfil.poll(sessions, d, log=msgs.append) == 2
    idx = st.read_index(d)
    assert [r["buyer"] for r in idx] == ["Ada Example", "Grace Sample"]
    log = [json.loads(l) for l in open(os.path.join(d, "fulfilled.jsonl"), encoding="utf-8")]
    assert [(r["session"], r["serial"]) for r in log] == [("cs_test_a1", "bat-aaaaaaaaaaaa"), ("cs_test_a2", "bat-bbbbbbbbbbbb")]
    assert fulfil.poll(sessions, d, log=msgs.append) == 0
    assert any("not complete and paid" in m for m in msgs) and any("livemode" in m for m in msgs)


def test_fetch_refuses_live_key():
    with pytest.raises(fulfil.Skip):
        fulfil.fetch_sessions("rk" + "_live_" + "x")


def test_poll_cli_needs_key(monkeypatch):
    monkeypatch.delenv("STRIPE_TEST_KEY", raising=False)
    assert fulfil.main(["fulfil.py", "--poll"]) == 2


def test_page_buy_button_is_test_mode_link():
    page = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    assert 'href="https://buy.stripe.com/test_' in page and "TEST MODE: no real charge" in page
    assert "word-break:break-all" in page and "second channel" in page
    assert "new (not in mathlib text)" in page.lower()
