"""Interop contract: C JSON export must pass exact JS Notes core shape, no I/O to Kobo."""
import json
import sys
from datetime import datetime

def check():
    payload = sys.stdin.read()
    book = json.loads(payload)
    assert set(book) == {"format", "notes"}, book.keys()
    assert book["format"] == "pmkb-notes-v1"
    assert len(book["notes"]) == 1
    n = book["notes"][0]
    assert set(n) == {"id","title","text","strokes","typography","created","updated"}
    assert n["id"] == "pmkb_000001"
    assert n["title"] == "Journal été"
    assert n["text"] == 'Bonjour\nΩ "test"'
    assert n["strokes"] == []
    assert n["typography"] == {"font":"mono","size":17,"lineHeight":1.6}
    assert n["created"] == n["updated"] == "2026-10-19T01:04:00.000Z"
    assert datetime.fromisoformat(n["created"].replace("Z","+00:00"))
    assert len(payload.encode("utf-8")) <= 3000000
    print("PMKB JSON: 1/1 compatible fixture PASS")

if __name__ == "__main__":
    check()
