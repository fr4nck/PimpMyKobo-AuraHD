"""Interop contract: C JSON export must pass exact JS Notes core shape, no I/O to Kobo."""
import json
import sys
import tempfile
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from notes_checkpoint_host import load_checkpoint, save_checkpoint

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
    data = payload.encode("utf-8")
    assert len(data) <= 3000000
    # Actual C11-generated JSON -> host-only staged checkpoint -> exact bytes.
    with tempfile.TemporaryDirectory(prefix="pmkb-native-json-") as tmp:
        destination = Path(tmp) / "notes"
        destination.mkdir()
        receipt = save_checkpoint(destination, data)
        recovered = load_checkpoint(destination)
        assert receipt["status"] == "host_snapshot_verified"
        assert recovered["payload"] == data
        assert recovered["sha256"] == receipt["sha256"]
        assert not receipt["notes_ui_saved"]
        assert not recovered["native_import_verified"]
        assert not recovered["physical_p3_verified"]
    print("PMKB JSON: 1/1 compatible fixture PASS")
    print("PMKB NOTES CHECKPOINT HOST: C11 JSON roundtrip PASS, P3 UNKNOWN")

if __name__ == "__main__":
    check()
