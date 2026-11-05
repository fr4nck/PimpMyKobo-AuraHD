import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "recover_live_bundle",
    ROOT / "tools" / "recover-live-bundle.py",
)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(mod)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_bundle(root: Path, *, tamper_candidate: bool = False) -> tuple[Path, bytes]:
    bundle = root / "opt" / "pmkb"
    bundle.mkdir(parents=True)

    candidate = b"PMKB synthetic candidate\n"
    expected_candidate = candidate
    image_name = "PMKB-FIRST-BOOT-1-test.img"

    manifest = {
        "head": "a" * 40,
        "image_name": image_name,
        "image_size": len(expected_candidate),
        "image_sha256": sha256_bytes(expected_candidate),
    }
    manifest_bytes = (json.dumps(manifest, sort_keys=True) + "\n").encode()

    plan = {
        "replacement_sha256": sha256_bytes(expected_candidate),
        "write_authorized": False,
        "physical_restore_eligible": False,
    }
    plan_bytes = (json.dumps(plan, sort_keys=True) + "\n").encode()

    identity = {
        "project": "PimpMyKobo-AuraHD",
        "head": "a" * 40,
        "image_name": image_name,
        "image_sha256": sha256_bytes(expected_candidate),
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "plan_sha256": sha256_bytes(plan_bytes),
    }
    identity_bytes = (json.dumps(identity, sort_keys=True) + "\n").encode()

    (bundle / "candidate.json").write_bytes(manifest_bytes)
    (bundle / "restore-plan.json").write_bytes(plan_bytes)
    (bundle / "BUILD-IDENTITY.json").write_bytes(identity_bytes)
    (bundle / image_name).write_bytes(candidate + (b"tampered" if tamper_candidate else b""))
    return bundle, expected_candidate


class RecoverLiveBundleTests(unittest.TestCase):
    def test_recovers_old_schema_bundle_from_live_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "live-root"
            _bundle, candidate = make_bundle(root)
            destination = Path(td) / "recovered"

            report = mod.recover(root, destination)

            self.assertEqual("live_root", report["source_kind"])
            self.assertEqual("PMKB-FIRST-BOOT-1-test.img", report["image_name"])
            self.assertEqual(sha256_bytes(candidate), report["image_sha256"])
            self.assertEqual(candidate, (destination / report["image_name"]).read_bytes())
            receipt = json.loads((destination / "RECOVERED-BUNDLE.json").read_text())
            self.assertEqual("recovered", receipt["status"])
            self.assertEqual("valid", receipt["validation_status"])
            self.assertEqual("read_only", receipt["source_access"])
            self.assertEqual(1, receipt["identity_schema"])

    def test_rejects_tampered_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "live-root"
            make_bundle(root, tamper_candidate=True)
            with self.assertRaises(mod.RecoveryError):
                mod.recover(root, Path(td) / "recovered")

    def test_refuses_nonempty_destination(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "live-root"
            make_bundle(root)
            destination = Path(td) / "recovered"
            destination.mkdir()
            (destination / "keep.txt").write_text("do not overwrite", encoding="utf-8")
            with self.assertRaises(mod.RecoveryError):
                mod.recover(root, destination)
            self.assertEqual(
                "do not overwrite",
                (destination / "keep.txt").read_text(encoding="utf-8"),
            )

    def test_refuses_dev_paths_before_any_read(self):
        with self.assertRaises(mod.RecoveryError):
            mod.ensure_regular_source(Path("/dev/sdz"))


if __name__ == "__main__":
    unittest.main()
