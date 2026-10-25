"""Pure synthetic tests for Store manifest; never install or execute a .pmkb."""
import importlib.util
import json
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / "experimental/store-v0/manifest_contract.py"
SPEC = importlib.util.spec_from_file_location("pmkb_store_manifest", MODULE)
STORE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STORE)
EXAMPLE = MODULE.parent / "example/manifest.json"


class StoreManifestTests(unittest.TestCase):
    def setUp(self):
        self.sample = json.loads(EXAMPLE.read_text(encoding="utf-8"))

    def _raw(self, **overrides):
        return json.dumps({**self.sample, **overrides}, ensure_ascii=False).encode("utf-8")

    def _reject(self, reason, **overrides):
        with self.assertRaises(STORE.ManifestError) as caught:
            STORE.read_manifest(self._raw(**overrides))
        self.assertEqual(reason, str(caught.exception))

    def test_example_valid_and_pure(self):
        raw = EXAMPLE.read_bytes()
        result = STORE.read_manifest(raw)
        self.assertEqual("org.pmkb.demo", result["id"])
        self.assertFalse(result["network"])
        self.assertEqual(raw, EXAMPLE.read_bytes())
        self.assertIsNot(result, self.sample)

    def test_refuse_wrong_manifest_version_even_boolean(self):
        for value in (0, 2, True, "1"):
            with self.subTest(value=value):
                self._reject("unsupported_manifest_version", manifest_version=value)

    def test_reject_unknown_missing_or_duplicate_keys(self):
        self._reject("invalid_fields", new_option=1)
        missing = dict(self.sample)
        del missing["entrypoint"]
        with self.assertRaisesRegex(STORE.ManifestError, "invalid_fields"):
            STORE.read_manifest(json.dumps(missing).encode("utf-8"))
        raw = EXAMPLE.read_bytes().replace(b'"network": false', b'"network": false, "network": true')
        with self.assertRaisesRegex(STORE.ManifestError, "duplicate_key"):
            STORE.read_manifest(raw)

    def test_reject_unsupported_target_or_runtime(self):
        self._reject("unsupported_target", target="clara-hd")
        self._reject("unsupported_runtime", runtime="android")
        self._reject("unsupported_runtime", runtime="qt6")

    def test_names_ids_and_versions_are_bounded(self):
        for field, value, reason in (
            ("id", "../escape", "invalid_id"),
            ("id", "com.EXAMPLE.demo", "invalid_id"),
            ("id", "single", "invalid_id"),
            ("name", "   ", "invalid_name"),
            ("name", "bad\nname", "invalid_name"),
            ("version", "1.2", "invalid_version"),
            ("version", "01.2.3", "invalid_version"),
        ):
            with self.subTest(field=field, value=value):
                self._reject(reason, **{field: value})

    def test_entrypoint_must_be_relative(self):
        for path in ("../run", "/bin/run", "bin/../../run", "bin//run",
                     "bin/./run", "bin\\run", "C:/bin/run", "bin/evil\x00"):
            with self.subTest(path=path):
                self._reject("invalid_entrypoint", entrypoint=path)

    def test_reject_missing_or_invalid_dependencies(self):
        self._reject("missing_dependencies", dependencies=["org.pmkb.reader"])
        self._reject("invalid_dependencies", dependencies=["org.pmkb.reader"] * 2)
        self._reject("invalid_dependencies", dependencies=["org.pmkb.demo"])
        self._reject("invalid_dependencies", dependencies=["BAD!"])
        self.assertEqual(["org.pmkb.reader"], STORE.read_manifest(
            self._raw(dependencies=["org.pmkb.reader"]),
            available_dependencies={"org.pmkb.reader"})["dependencies"])

    def test_network_is_explicit_opt_in(self):
        self._reject("network_not_granted", network=True)
        self._reject("invalid_network_permission", network="yes")
        result = STORE.read_manifest(self._raw(network=True), allow_network=True)
        self.assertIs(result["network"], True)

    def test_size_utf8_json_and_input_types(self):
        for payload in (b"", b"x" * 4097, b"\xff", b"[1,2]", b"{", None):
            with self.subTest(payload=repr(payload)[:40]):
                with self.assertRaises(STORE.ManifestError):
                    STORE.read_manifest(payload)

    def test_no_side_effects_when_parsing(self):
        from unittest.mock import patch
        raw = self._raw()
        with patch("builtins.open", side_effect=AssertionError("I/O")), \
             patch("subprocess.run", side_effect=AssertionError("process")):
            parsed = STORE.read_manifest(raw)
        self.assertEqual("bin/demo", parsed["entrypoint"])


if __name__ == "__main__":
    unittest.main()
