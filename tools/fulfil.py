#!/usr/bin/env python3
"""Fulfil a Stripe TEST-mode checkout.session.completed event: claim a reserved lemma for the buyer.

Usage: python tools/fulfil.py <event.json> [--dir stock]
       python tools/fulfil.py --poll [--link plink_...] [--dir stock]   (default link plink_1UZhjiAEYFnTYpgAkqQ7MbPE; env STRIPE_TEST_KEY, test mode only)
Reads a webhook JSON file only (no network, no Stripe key needed). A real webhook endpoint must
verify the Stripe-Signature header before calling fulfil() -- see web/checkout.md.
Exit: 0 fulfilled, 2 bad/unsupported event, 3 already fulfilled, 4 stock empty.
"""
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from buyatheorem import stock  # noqa: E402


DEFAULT_LINK = "plink_1UZhjiAEYFnTYpgAkqQ7MbPE"


class Skip(Exception):
    def __init__(self, rc, msg):
        super().__init__(msg)
        self.rc = rc


def _claim(sid: str, name: str, d: str) -> str:
    log = os.path.join(d, "fulfilled.jsonl")
    if os.path.exists(log) and any(json.loads(l)["session"] == sid for l in open(log, encoding="utf-8") if l.strip()):
        raise Skip(3, "session already fulfilled")
    try:
        serial = stock.next_reserved(d)
    except LookupError:
        raise Skip(4, "stock empty")
    stock.claim(serial, name, d)
    with open(log, "a", encoding="utf-8", newline=chr(10)) as f:
        f.write(json.dumps({"session": sid, "serial": serial, "buyer": name}) + chr(10))
    return serial


def session_name(obj: dict) -> str:
    for fld in obj.get("custom_fields") or []:
        if fld.get("key") == "buyer_name":
            return ((fld.get("text") or {}).get("value") or "").strip()
    return ((obj.get("metadata") or {}).get("buyer_name") or "").strip()


def fulfil_session(obj: dict, d: str) -> str:
    if obj.get("status", "complete") != "complete" or obj.get("payment_status") != "paid":
        raise Skip(2, "not complete and paid")
    if obj.get("livemode") is not False:
        raise Skip(2, "livemode session refused: test mode only")
    name, sid = session_name(obj), obj.get("id", "")
    if not name or not sid:
        raise Skip(2, "missing buyer_name or session id")
    return _claim(sid, name, d)


def fetch_sessions(key: str, link: str = DEFAULT_LINK) -> list:
    if "_live_" in key:
        raise Skip(2, "live key refused: test mode only")
    q = {"status": "complete", "limit": "100"}
    if link:
        q["payment_link"] = link
    req = urllib.request.Request("https://api.stripe.com/v1/checkout/sessions?" + urllib.parse.urlencode(q),
                                 headers={"Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get("data", [])


def poll(sessions: list, d: str, log=print) -> int:
    """Claim stock for each completed, paid test session. Idempotent on session id. Returns claims made."""
    n = 0
    for obj in sorted(sessions, key=lambda o: o.get("created", 0)):
        try:
            serial = fulfil_session(obj, d)
            log(f"{obj.get('id')} -> {serial}")
            n += 1
        except Skip as e:
            log(f"{obj.get('id')}: skip ({e})")
    return n


def fulfil(event: dict, d: str) -> str:
    if event.get("type") != "checkout.session.completed":
        raise Skip(2, "unsupported event type")
    obj = event.get("data", {}).get("object", {})
    if obj.get("payment_status") != "paid":
        raise Skip(2, "not paid")
    if event.get("livemode") is True or obj.get("livemode") is True:
        raise Skip(2, "livemode event refused: test mode only")
    name = (obj.get("metadata") or {}).get("buyer_name", "").strip()
    sid = obj.get("id", "")
    if not name or not sid:
        raise Skip(2, "missing buyer_name metadata or session id")
    return _claim(sid, name, d)


def main(argv):
    d = argv[argv.index("--dir") + 1] if "--dir" in argv else "stock"
    if "--poll" in argv:
        key = os.environ.get("STRIPE_TEST_KEY")
        if not key:
            print("error: set STRIPE_TEST_KEY", file=sys.stderr)
            return 2
        link = argv[argv.index("--link") + 1] if "--link" in argv else DEFAULT_LINK
        try:
            poll(fetch_sessions(key, link), d)
            return 0
        except (Skip, OSError, ValueError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
    try:
        ev = json.load(open(argv[1], encoding="utf-8"))
        print(fulfil(ev, d))
        return 0
    except Skip as e:
        print(f"skip: {e}", file=sys.stderr)
        return e.rc
    except (OSError, ValueError, IndexError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
