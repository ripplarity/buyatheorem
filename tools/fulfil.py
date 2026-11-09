#!/usr/bin/env python3
"""Fulfil a Stripe TEST-mode checkout.session.completed event: claim a reserved lemma for the buyer.

Usage: python tools/fulfil.py <event.json> [--dir stock]
Reads a webhook JSON file only (no network, no Stripe key needed). A real webhook endpoint must
verify the Stripe-Signature header before calling fulfil() -- see web/checkout.md.
Exit: 0 fulfilled, 2 bad/unsupported event, 3 already fulfilled, 4 stock empty.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from buyatheorem import stock  # noqa: E402


class Skip(Exception):
    def __init__(self, rc, msg):
        super().__init__(msg)
        self.rc = rc


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
    log = os.path.join(d, "fulfilled.jsonl")
    if os.path.exists(log) and any(json.loads(l)["session"] == sid for l in open(log, encoding="utf-8") if l.strip()):
        raise Skip(3, "session already fulfilled")
    try:
        serial = stock.next_reserved(d)
    except LookupError:
        raise Skip(4, "stock empty")
    stock.claim(serial, name, d)
    with open(log, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"session": sid, "serial": serial, "buyer": name}) + "\n")
    return serial


def main(argv):
    d = argv[argv.index("--dir") + 1] if "--dir" in argv else "stock"
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
