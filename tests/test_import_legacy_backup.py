import copy
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load(name, script):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


legacy = load("legacy", "import-legacy-backup.py")
rebuild = load("rebuild", "rebuild-rootfs.py")


def make_pre(path, p1_size=268435968, p2_size=268435968, p3_size=31368150016):
    offset = 9961472
    data = bytearray(offset)
    data[510:512] = b"\x55\xaa"
    for index, (ptype, size) in enumerate(((0x83, p1_size), (0x83, p2_size), (0x0B, p3_size))):
        entry = 446 + 16 * index
        data[entry + 4] = ptype
        data[entry + 8:entry + 12] = (offset // 512).to_bytes(4, "little")
        data[entry + 12:entry + 16] = (size // 512).to_bytes(4, "little")
        offset += size
    hw_offset = 0x80000
    data[hw_offset:hw_offset + 16] = b"HW CONFIG v1.7\x00\x27"
    data[hw_offset + 16] = 28
    path.write_bytes(data)


def imported_manifest(pre, p2, path):
    data = legacy.qualify(pre, p2, legacy.digest(pre), legacy.digest(p2))
    for component, source in zip(data["components"], (pre, p2)):
        component["file"] = os.path.relpath(source, path.parent)
    path.write_text(json.dumps(data), encoding="utf-8")
    return data


class LegacyImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pre = self.root / "pré P1.bin"
        self.p2 = self.root / "P2 recovery.img"
        make_pre(self.pre, p2_size=4096)
        sb = bytearray(4096)
        for offset, size, value in ((1028, 4, 3), (1048, 4, 0), (1080, 2, 0xEF53),
                                    (1100, 4, 1), (1112, 2, 128), (1120, 4, 0x44)):
            sb[offset:offset + size] = value.to_bytes(size, "little")
        self.p2.write_bytes(sb)
        self.manifest = self.root / "legacy.json"
        self.pre_sha = legacy.digest(self.pre)
        self.p2_sha = legacy.digest(self.p2)

    def qualify(self):
        return legacy.qualify(self.pre, self.p2, self.pre_sha, self.p2_sha)

    def test_honest_contract_and_real_geometry(self):
        data = self.qualify()
        self.assertFalse(data["complete"])
        self.assertTrue(data["qualified_for_rebuild"])
        self.assertFalse(data["provenance"]["physical_restore_eligible"])
        self.assertEqual("declared_not_verified", data["provenance"]["association"])
        self.assertNotIn("target_fingerprint", data)
        self.assertEqual(268435968, data["mbr"]["partitions"][0]["size"])
        self.assertFalse(data["mbr"]["source_capacity_verified"])
        self.assertNotIn("beyond_end", data["mbr"]["partitions"][0])
        self.assertEqual(["not_qualified"] * 2, [c["status"] for c in data["components"][2:]])
        self.assertEqual("not_checked", data["checks"]["recovery_artifacts"])
        self.assertEqual((1024, 128), tuple(data["components"][1]["ext4_superblock"][k] for k in ("block_size", "inode_size")))
        self.assertTrue(data["components"][1]["ext4_superblock"]["needs_recovery"])

    def test_hash_mismatch_and_invalid_declarations(self):
        for sha in ("0" * 64, "bad", None):
            with self.subTest(sha=sha), self.assertRaises(ValueError):
                legacy.qualify(self.pre, self.p2, sha, self.p2_sha)

    def test_mbr_identity_size_and_ext4_fail_closed(self):
        for target, offset, value in ((self.pre, 510, b"\x00"), (self.pre, 0x80010, b"\x1d"),
                                      (self.pre, 446 + 8, (19457).to_bytes(4, "little")),
                                      (self.pre, 462 + 12, (9).to_bytes(4, "little")),
                                      (self.p2, 1080, b"\x00"), (self.p2, 1028, (99).to_bytes(4, "little")),
                                      (self.p2, 1048, (99).to_bytes(4, "little")),
                                      (self.p2, 1112, (129).to_bytes(2, "little"))):
            original = target.read_bytes()
            changed = bytearray(original); changed[offset:offset + len(value)] = value
            target.write_bytes(changed)
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                legacy.qualify(self.pre, self.p2, legacy.digest(self.pre), legacy.digest(self.p2))
            target.write_bytes(original)

    def test_device_paths_rejected_before_open(self):
        for path in ("/dev/sdb", r"\\.\PhysicalDrive2", r"\\?\GLOBALROOT\Device\Harddisk0", r"\\server\share\x"):
            with self.subTest(path=path), mock.patch.object(Path, "open", side_effect=AssertionError("opened")):
                with self.assertRaises(ValueError):
                    legacy.digest(Path(path))

    @unittest.skipUnless(sys.platform == "linux", "Linux symlink/FIFO checks")
    def test_device_alias_and_fifo_refused(self):
        alias = self.root / "alias"
        alias.symlink_to("/dev/zero")
        fifo = self.root / "fifo"
        os.mkfifo(fifo)
        for path in (alias, fifo):
            with mock.patch.object(Path, "open", side_effect=AssertionError("opened")), self.assertRaises(ValueError):
                legacy.digest(path)

    def test_inputs_are_only_read_no_subprocess_or_output(self):
        original_open = Path.open
        def guarded(path, mode="r", *args, **kwargs):
            self.assertNotIn("+", mode)
            self.assertFalse(any(flag in mode for flag in "wax"))
            return original_open(path, mode, *args, **kwargs)
        with mock.patch.object(Path, "open", guarded), mock.patch.object(subprocess, "run", side_effect=AssertionError("external command")):
            self.qualify()
        self.assertEqual(self.pre_sha, legacy.digest(self.pre))
        self.assertEqual(self.p2_sha, legacy.digest(self.p2))
        self.assertFalse(self.manifest.exists())

    def test_acceptance_requires_opt_in_and_rechecks_evidence(self):
        imported_manifest(self.pre, self.p2, self.manifest)
        output = self.root / "out.img"
        result = rebuild.preflight(self.manifest, self.p2, output)
        self.assertEqual("failed", result["status"])
        self.assertTrue(any("--accept-legacy-import" in e for e in result["errors"]))
        result = rebuild.preflight(self.manifest, self.p2, output, accept_legacy_import=True)
        self.assertEqual("ready", result["status"], result)
        self.assertFalse(result["physical_restore_eligible"])
        self.assertFalse(output.exists())
        self.pre.write_bytes(b"tampered")
        self.assertEqual("failed", rebuild.preflight(self.manifest, self.p2, output, accept_legacy_import=True)["status"])

    def test_tampered_contract_geometry_claims_and_duplicate_components_refused(self):
        original = imported_manifest(self.pre, self.p2, self.manifest)
        for mutate in (lambda d: d.update(complete=True), lambda d: d.update(status="complete"),
                       lambda d: d["provenance"].update(physical_restore_eligible=True),
                       lambda d: d["mbr"]["partitions"][0].update(size=1024),
                       lambda d: d["checks"].update(recovery_artifacts=True),
                       lambda d: d["components"].append(d["components"][1]),
                       lambda d: d.update(contract="unknown"),
                       lambda d: d.update(target_fingerprint={"sha256": "0" * 64}),
                       lambda d: d.update(tool="backup-aura-hd")):
            data = copy.deepcopy(original); mutate(data)
            self.manifest.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual("failed", rebuild.preflight(self.manifest, self.p2, self.root / "out", accept_legacy_import=True)["status"])

    def test_cli_explicit_declaration_exclusive_output_and_no_clobber(self):
        args = [str(self.pre), str(self.p2), str(self.manifest), "--expected-pre-p1-sha256", self.pre_sha,
                "--expected-p2-sha256", self.p2_sha]
        with mock.patch.object(sys, "argv", ["import", *args]), self.assertRaises(SystemExit):
            legacy.main()
        with mock.patch.object(sys, "argv", ["import", *args, "--declare-same-source"]), mock.patch("builtins.print"):
            self.assertEqual(0, legacy.main())
            before = self.manifest.read_bytes()
            self.assertEqual(1, legacy.main())
            self.assertEqual(before, self.manifest.read_bytes())
        self.assertEqual("ready", rebuild.preflight(self.manifest, self.p2, self.root / "out", accept_legacy_import=True)["status"])

    def test_bad_input_does_not_create_manifest(self):
        with mock.patch.object(sys, "argv", ["import", str(self.pre), str(self.p2), str(self.manifest),
                   "--expected-pre-p1-sha256", "0" * 64, "--expected-p2-sha256", self.p2_sha,
                   "--declare-same-source"]), mock.patch("builtins.print"):
            self.assertEqual(1, legacy.main())
        self.assertFalse(self.manifest.exists())


if __name__ == "__main__":
    unittest.main()
