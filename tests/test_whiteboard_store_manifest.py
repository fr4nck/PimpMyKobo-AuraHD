"""Store declaration contract: metadata only, no executable or install."""
import importlib.util
from io import BytesIO
from zipfile import ZipFile
import sys
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "experimental" / "store-v0"
sys.path.insert(0, str(STORE))
spec = importlib.util.spec_from_file_location("pmkb_store_manifest", STORE / "manifest_contract.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


from archive_contract import ArchiveError, inspect_archive


class WhiteboardStoreManifestTests(unittest.TestCase):
    def test_manifest_is_compatible_metadata_only(self):
        source = STORE / "example" / "whiteboard-manifest.json"
        raw = source.read_bytes()
        manifest = module.read_manifest(raw)
        self.assertEqual(manifest["id"], "org.pmkb.whiteboard")
        self.assertEqual(manifest["target"], "dragon")
        self.assertEqual(manifest["runtime"], "pmkb-ui-v0")
        self.assertEqual(manifest["network"], False)
        self.assertEqual(manifest["dependencies"], [])
        self.assertEqual(manifest["entrypoint"], "bin/pmkb-whiteboard")
        self.assertFalse((STORE / "example" / manifest["entrypoint"]).exists(),
                         "Demo must not claim an installed ARM executable")

    def test_manifest_alone_is_not_a_installable_package(self):
        manifest = (STORE / "example" / "whiteboard-manifest.json").read_bytes()
        archive = BytesIO()
        with ZipFile(archive, "w") as zf:
            zf.writestr("manifest.json", manifest)
        with self.assertRaises(ArchiveError) as failure:
            inspect_archive(archive.getvalue())
        self.assertEqual(str(failure.exception), "missing_entrypoint")

    def test_incompatible_or_network_variants_are_rejected(self):
        source = STORE / "example" / "whiteboard-manifest.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        for field, value, reason in (
            ("target", "other", "unsupported_target"),
            ("runtime", "unknown", "unsupported_runtime"),
            ("network", True, "network_not_granted"),
            ("entrypoint", "../unsafe", "invalid_entrypoint"),
        ):
            with self.subTest(field=field):
                altered = dict(data, **{field: value})
                with self.assertRaises(module.ManifestError) as caught:
                    module.read_manifest(json.dumps(altered).encode("utf-8"))
                self.assertEqual(str(caught.exception), reason)


if __name__ == "__main__":
    unittest.main()
