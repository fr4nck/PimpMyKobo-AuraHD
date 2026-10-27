"""Host-only checkpoint tests: synthetic bytes, temporary directories only."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / "experimental" / "native-ui" / "tools"
sys.path.insert(0, str(TOOLS))
from notes_checkpoint_host import (  # noqa: E402
    CURRENT, PREVIOUS, CheckpointError, load_checkpoint, save_checkpoint,
    validate_native_snapshot,
)


def note(number=1, title="Journal été", body='Bonjour\nΩ "test"'):
    return {
        "id": f"pmkb_{number:06d}", "title": title, "text": body,
        "strokes": [],
        "typography": {"font": "mono", "size": 17, "lineHeight": 1.6},
        "created": "2026-10-19T01:04:00.000Z",
        "updated": "2026-10-19T01:04:00.000Z",
    }


def snapshot(*notes):
    return json.dumps({"format": "pmkb-notes-v1", "notes": list(notes)},
                      ensure_ascii=False, separators=(",", ":")).encode("utf-8")


class NativeNotesCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pmkb-notes-tests-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / "host-notes"
        self.directory.mkdir()

    def test_exact_native_json_bytes_survive_save_and_load(self):
        data = snapshot(note(body="Été\nΩ ♥"))
        receipt = save_checkpoint(self.directory, data)
        self.assertEqual(receipt["sha256"], hashlib.sha256(data).hexdigest())
        self.assertFalse(receipt["notes_ui_saved"])
        self.assertFalse(receipt["physical_p3_verified"])
        self.assertFalse(receipt["native_import_verified"])
        read = load_checkpoint(self.directory)
        self.assertEqual(read["payload"], data)
        self.assertEqual(read["source"], "current")
        self.assertFalse(read["recovery_required"])
        self.assertFalse(read["physical_p3_verified"])
        self.assertEqual(list(self.directory.iterdir()),
                         [self.directory / CURRENT])

    def test_previous_valid_copy_is_kept_during_update(self):
        first, second = snapshot(note(body="1")), snapshot(note(body="2"))
        initial = save_checkpoint(self.directory, first)
        saved = save_checkpoint(self.directory, second,
                                expected_current_sha256=initial["sha256"])
        self.assertTrue(saved["previous_retained"])
        self.assertEqual(load_checkpoint(self.directory)["payload"], second)
        (self.directory / CURRENT).write_bytes(b"tampered")
        recovered = load_checkpoint(self.directory)
        self.assertEqual(recovered["payload"], first)
        self.assertEqual(recovered["source"], "previous")
        self.assertTrue(recovered["recovery_required"])
        self.assertFalse(recovered["native_import_verified"])

    def test_missing_primary_does_not_destroy_previous(self):
        first, second = snapshot(note(body="A")), snapshot(note(body="B"))
        sha = save_checkpoint(self.directory, first)["sha256"]
        save_checkpoint(self.directory, second, expected_current_sha256=sha)
        (self.directory / CURRENT).unlink()
        self.assertEqual(load_checkpoint(self.directory)["payload"], first)
        with self.assertRaisesRegex(CheckpointError,
                                    "recovery_required_before_next_save"):
            save_checkpoint(self.directory, second)

    def test_fault_before_first_publish_cleans_stage(self):
        def crash():
            raise RuntimeError("synthetic crash before publish")
        with self.assertRaisesRegex(RuntimeError, "synthetic crash"):
            save_checkpoint(self.directory, snapshot(note()),
                            before_publish=crash)
        self.assertEqual(list(self.directory.iterdir()), [])
        with self.assertRaises(CheckpointError):
            load_checkpoint(self.directory)

    def test_fault_before_update_preserves_both_existing_slots(self):
        first, second, third = (snapshot(note(body=v)) for v in "ABC")
        sha = save_checkpoint(self.directory, first)["sha256"]
        sha2 = save_checkpoint(self.directory, second,
                               expected_current_sha256=sha)["sha256"]
        files_before = {
            name: (self.directory / name).read_bytes()
            for name in (CURRENT, PREVIOUS)
        }
        with self.assertRaisesRegex(RuntimeError, "injected"):
            save_checkpoint(self.directory, third,
                            expected_current_sha256=sha2,
                            before_publish=lambda: (_ for _ in ()).throw(
                                RuntimeError("injected")))
        files_after = {
            name: (self.directory / name).read_bytes()
            for name in (CURRENT, PREVIOUS)
        }
        self.assertEqual(files_before, files_after)
        self.assertEqual(sorted(p.name for p in self.directory.iterdir()),
                         sorted((CURRENT, PREVIOUS)))

    def test_stale_writer_must_supply_current_sha(self):
        first = snapshot(note(body="initial"))
        save_checkpoint(self.directory, first)
        with self.assertRaisesRegex(CheckpointError, "stale_snapshot"):
            save_checkpoint(self.directory, snapshot(note(body="overwrite")))
        with self.assertRaisesRegex(CheckpointError, "stale_snapshot"):
            save_checkpoint(self.directory, snapshot(note(body="other")),
                            expected_current_sha256="0" * 64)
        self.assertEqual(load_checkpoint(self.directory)["payload"], first)

    def test_corrupted_current_cannot_be_overwritten_silently(self):
        first = snapshot(note(body="safe"))
        sha = save_checkpoint(self.directory, first)["sha256"]
        (self.directory / CURRENT).write_bytes(b"broken")
        with self.assertRaises(CheckpointError):
            save_checkpoint(self.directory, snapshot(note(body="new")),
                            expected_current_sha256=sha)
        with self.assertRaises(CheckpointError):
            load_checkpoint(self.directory)

    def test_corrupted_previous_blocks_overwrite(self):
        first, second, third = (snapshot(note(body=v)) for v in "ABC")
        old_sha = save_checkpoint(self.directory, first)["sha256"]
        new_sha = save_checkpoint(
            self.directory, second, expected_current_sha256=old_sha)["sha256"]
        (self.directory / PREVIOUS).write_bytes(b"broken backup")
        with self.assertRaises(CheckpointError):
            save_checkpoint(self.directory, third,
                            expected_current_sha256=new_sha)
        self.assertEqual(load_checkpoint(self.directory)["payload"], second)

    def test_current_symlink_is_never_followed(self):
        outside = Path(self.temp.name) / "sentinel"
        outside.write_bytes(snapshot(note()))
        try:
            os.symlink(outside, self.directory / CURRENT)
        except (NotImplementedError, OSError):
            self.skipTest("symlink creation unavailable on this Windows runner")
        with self.assertRaises(CheckpointError):
            save_checkpoint(self.directory, snapshot(note()))
        self.assertEqual(outside.read_bytes(), snapshot(note()))

    def test_directory_outside_system_temp_is_refused(self):
        with self.assertRaisesRegex(CheckpointError,
                                    "not_a_host_test_directory"):
            save_checkpoint(Path.cwd(), snapshot(note()))
        with self.assertRaisesRegex(CheckpointError,
                                    "not_a_host_test_directory"):
            load_checkpoint(Path.cwd())

    def test_no_path_based_cli_or_device_operations(self):
        source = (TOOLS / "notes_checkpoint_host.py").read_text()
        self.assertNotIn("argparse", source)
        self.assertNotIn("/dev/", source)
        self.assertNotIn("subprocess", source)
        self.assertNotIn("mount(", source)
        self.assertNotIn("os.system", source)

    def test_invalid_and_non_native_format_never_get_written(self):
        invalid = [
            b"", b"\xff",
            b'{"format":"pmkb-notes-v1","format":"other","notes":[]}',
            b'{"format":"wrong","notes":[]}',
            b'{"format":"pmkb-notes-v1","notes":[null]}',
            b'{"format":"pmkb-notes-v1","notes":[],"extra":1}',
            snapshot(note(title="\u2009\ufeff")),
            snapshot(note(title="x" * 101)),
            snapshot(note(body="\u03a9" * 120001)),
            snapshot(note(number=1), note(number=1)),
            snapshot(note(number=0)),
            snapshot(note()) + b"garbage",
            b'{"format":"pmkb-notes-v1","notes":[],"extra":NaN}',
        ]
        for data in invalid:
            with self.subTest(data=data[:60]):
                with self.assertRaises(CheckpointError):
                    save_checkpoint(self.directory, data)
                self.assertFalse((self.directory / CURRENT).exists())

    def test_unsupported_browser_sketch_and_typography_are_refused(self):
        painted = note()
        painted["strokes"] = [{"points": [1, 2]}]
        different_font = note()
        different_font["typography"]["font"] = "serif"
        for n in (painted, different_font):
            with self.subTest(value=n):
                with self.assertRaises(CheckpointError):
                    validate_native_snapshot(snapshot(n))

    def test_timestamp_calendar_and_unicode_validation(self):
        bad_date = note()
        bad_date["created"] = "2026-02-30T01:04:00.000Z"
        surrogate = '{"format":"pmkb-notes-v1","notes":['
        for n in (bad_date,):
            with self.assertRaises(CheckpointError):
                validate_native_snapshot(snapshot(n))
        # JSON parser may decode an escaped lone surrogate, but C11 cannot.
        native = json.loads(snapshot(note()))
        native["notes"][0]["text"] = "\ud800"
        bytes_data = json.dumps(native).encode("ascii")
        with self.assertRaises(CheckpointError):
            validate_native_snapshot(bytes_data)

    def test_unreadable_format_does_not_count_as_restored(self):
        with self.assertRaises(CheckpointError):
            load_checkpoint(self.directory)
        (self.directory / CURRENT).write_bytes(snapshot(note()))
        with self.assertRaises(CheckpointError):
            load_checkpoint(self.directory)
        self.assertFalse((self.directory / PREVIOUS).exists())

    def test_empty_carnet_is_valid(self):
        data = snapshot()
        self.assertEqual(validate_native_snapshot(data)["notes"], [])
        save_checkpoint(self.directory, data)
        self.assertEqual(load_checkpoint(self.directory)["payload"], data)


if __name__ == "__main__":
    unittest.main()
