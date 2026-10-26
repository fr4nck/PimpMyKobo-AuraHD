"""L06-D1: read-only UI handoff tests, no graphical or executable Store."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'experimental' / 'store-v0'
sys.path.insert(0, str(SOURCE))
from store_view_contract import (SCHEMA, MAX_VIEW_BYTES, StoreViewError,
                                 encode_store_view, snapshot_store_view)


def entry(app_id='org.pmkb.demo', label='Demo', version='0.1.0', network=False):
    return {'id': app_id, 'name': label, 'version': version,
            'entrypoint': 'bin/demo', 'network_declared': network,
            'state': 'installed_unverified'}


def catalog(items=(), pending=()):
    return {'scope': 'synthetic_read_only', 'installed': items,
            'cleanup_pending': pending}


class StoreViewTests(unittest.TestCase):
    def decoded(self, value):
        raw = encode_store_view(value)
        self.assertIs(type(raw), bytes)
        self.assertLessEqual(len(raw), MAX_VIEW_BYTES)
        self.assertEqual(raw.decode('ascii').encode('ascii'), raw)
        return json.loads(raw)

    def test_empty_view_has_version_and_zero_count(self):
        result = self.decoded(catalog())
        self.assertEqual(SCHEMA, result['schema'])
        self.assertEqual('synthetic_read_only', result['scope'])
        self.assertEqual([], result['items'])
        self.assertEqual(0, result['cleanup_pending_count'])

    def test_inert_row_omits_entrypoint_and_actions(self):
        raw = encode_store_view(catalog((entry(),)))
        self.assertNotIn(b'bin/demo', raw)
        result = json.loads(raw)
        self.assertEqual('org.pmkb.demo', result['items'][0]['id'])
        self.assertIs(result['items'][0]['launchable'], False)
        self.assertEqual('installed_unverified', result['items'][0]['state'])
        self.assertNotIn('entrypoint', result['items'][0])
        self.assertNotIn('install', result)

    def test_network_is_descriptive_not_granted(self):
        result = self.decoded(catalog((entry(network=True),)))
        self.assertTrue(result['items'][0]['network_declared'])
        self.assertFalse(result['items'][0]['launchable'])

    def test_pending_names_are_private_count_only(self):
        items = ('.pmkb-remove-secret-123', '.pmkb-remove-other')
        raw = encode_store_view(catalog((), items))
        self.assertEqual(2, json.loads(raw)['cleanup_pending_count'])
        self.assertNotIn(b'secret', raw)
        self.assertNotIn(b'.pmkb-remove', raw)

    def test_unicode_and_escaped_label_stays_json_data(self):
        label = 'M\u00e9t\u00e9o <script>"\n&'
        result = self.decoded(catalog((entry(label=label),)))
        self.assertEqual(label, result['items'][0]['label'])

    def test_stable_order_and_repeatable_wire(self):
        unsorted = catalog((entry('org.pmkb.z', 'Z'),
                            entry('org.pmkb.a', 'A')))
        raw = encode_store_view(unsorted)
        self.assertEqual(raw, encode_store_view(unsorted))
        self.assertEqual(['org.pmkb.a', 'org.pmkb.z'],
                         [r['id'] for r in json.loads(raw)['items']])

    def test_rejects_invalid_catalog_scope_and_shape(self):
        for candidate in (None, {}, catalog(items='wrong'),
                          catalog(pending='wrong'), {'scope': 'device'}):
            with self.subTest(value=str(candidate)[:50]):
                with self.assertRaisesRegex(StoreViewError, 'invalid_view_source'):
                    encode_store_view(candidate)

    def test_rejects_duplicated_app_or_pending(self):
        with self.assertRaisesRegex(StoreViewError, 'invalid_view_source'):
            encode_store_view(catalog((entry(), entry())))
        with self.assertRaisesRegex(StoreViewError, 'invalid_view_source'):
            encode_store_view(catalog(pending=('.pmkb-remove-x', '.pmkb-remove-x')))

    def test_rejects_bad_row_metadata_and_excess_count(self):
        for bad in ({**entry(), 'state': 'runnable'},
                    {**entry(), 'network_declared': 'yes'},
                    {**entry(), 'id': None},
                    {**entry(), 'extraneous': 1}):
            with self.subTest(value=str(bad)[:70]):
                with self.assertRaisesRegex(StoreViewError, 'invalid_view_source'):
                    encode_store_view(catalog((bad,)))
        with self.assertRaisesRegex(StoreViewError, 'invalid_view_source'):
            encode_store_view(catalog(tuple(entry(f'org.pmkb.app{i}') for i in range(65))))

    def test_overflow_fails_not_truncated(self):
        # 64 names at 80 emojis are legal character lengths but exceed wire cap.
        giant = tuple(entry(f'org.pmkb.app{i}', label='\U0001f642' * 80)
                      for i in range(64))
        with self.assertRaisesRegex(StoreViewError, 'view_too_large'):
            encode_store_view(catalog(giant))

    def test_snapshot_uses_catalog_once_and_keeps_errors(self):
        source = catalog((entry(),))
        with patch('store_view_contract.read_catalog', return_value=source) as read:
            raw = snapshot_store_view('/tmp/synthetic-marker')
        read.assert_called_once_with('/tmp/synthetic-marker')
        self.assertEqual('Demo', json.loads(raw)['items'][0]['label'])
        with patch('store_view_contract.read_catalog', side_effect=ValueError('unsafe')):
            with self.assertRaisesRegex(ValueError, 'unsafe'):
                snapshot_store_view('/tmp/synthetic-marker')

    def test_no_subprocess_or_network(self):
        with patch('subprocess.run', side_effect=AssertionError('process')), \
             patch('socket.socket', side_effect=AssertionError('network')):
            self.assertEqual(0, self.decoded(catalog())['cleanup_pending_count'])


if __name__ == '__main__':
    unittest.main()
