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
