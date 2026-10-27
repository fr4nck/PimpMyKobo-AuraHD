"""L04-C: one synthetic chronology interpreted by the two pure contracts.

No device, clock, radio, SDIO or filesystem operation is performed by replay.
Consistent event claims are not proof of actual E606C0 hardware behavior.
"""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / 'experimental/power-lab'


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


NETWORK = load('network_sleep_contract')
ORDER = load('resume_order_contract')


class NetworkResumeIntegrationTests(unittest.TestCase):
    def evaluate(self, chronology):
        # Each pure replay receives only its known events, in original order.
        self.assertLessEqual(len(chronology), 128)
        self.assertTrue(set(chronology) <= NETWORK.ALLOWED | ORDER.EVENTS)
        network = NETWORK.replay([e for e in chronology if e in NETWORK.ALLOWED])
        order = ORDER.replay([e for e in chronology if e in ORDER.EVENTS])
        return network, order

    def test_explicit_wifi_after_resume_and_rtc_sync(self):
        seq = ['rtc_untrusted', 'mmc_ready', 'sdio_ready',
               'network_request', 'wifi_on', 'wifi_off', 'network_release',
               'sdio_quiesced', 'suspend', 'resume',
               'mmc_ready', 'sdio_ready', 'time_source_confirmed',
               'rtc_sync_confirmed', 'network_request', 'wifi_on']
        net, order = self.evaluate(seq)
        self.assertEqual(('consistent_unverified', 'consistent_unverified'),
                         (net['status'], order['status']))
        self.assertTrue(net['wifi_symbolically_on'])
        self.assertTrue(order['sdio_symbolically_ready'])
        self.assertTrue(order['rtc_trusted_claim'])
        self.assertEqual(1, net['resume_count'])
        for result in (net, order):
            self.assertIs(result['hardware_verified'], False)
            self.assertIs(result['rtc_verified'], False)

    def test_mmc_reinitialization_revokes_stale_sdio(self):
        seq = ['mmc_ready', 'sdio_ready', 'network_request',
               'mmc_ready', 'wifi_on']
        net, order = self.evaluate(seq)
        self.assertEqual('sdio_not_ready', net['error'])
        self.assertEqual('consistent_unverified', order['status'])
        self.assertFalse(order['sdio_symbolically_ready'])
        net, order = self.evaluate(seq[:-1] + ['sdio_ready', 'wifi_on'])
        self.assertEqual('consistent_unverified', net['status'])
        self.assertEqual('consistent_unverified', order['status'])

    def test_quiescence_cancels_pending_network_request(self):
        seq = ['mmc_ready', 'sdio_ready', 'network_request',
               'sdio_quiesced', 'wifi_on']
        net, order = self.evaluate(seq)
        self.assertEqual('no_explicit_request', net['error'])
        self.assertEqual('consistent_unverified', order['status'])
        net, order = self.evaluate(seq[:-1] + [
            'mmc_ready', 'sdio_ready', 'network_request', 'wifi_on'])
        self.assertEqual('consistent_unverified', net['status'])
        self.assertEqual('consistent_unverified', order['status'])

    def test_active_radio_blocks_host_reset_and_quiescence(self):
        for final in ('sdio_quiesced', 'mmc_ready'):
            with self.subTest(event=final):
                net, _ = self.evaluate([
                    'mmc_ready', 'sdio_ready', 'network_request',
                    'wifi_on', final])
                self.assertEqual('wifi_still_enabled', net['error'])

    def test_no_automatic_reconnection_after_resume(self):
        seq = ['mmc_ready', 'sdio_ready', 'network_request', 'wifi_on',
               'wifi_off', 'sdio_quiesced', 'suspend', 'resume',
               'mmc_ready', 'sdio_ready', 'wifi_on']
        net, order = self.evaluate(seq)
        self.assertEqual('no_explicit_request', net['error'])
        self.assertEqual('consistent_unverified', order['status'])

    def test_sdio_claim_without_mmc_proof_is_rejected_by_order_model(self):
        net, order = self.evaluate(['network_request', 'sdio_ready', 'wifi_on'])
        # The network-only model trusts its SDIO-ready event; consumers must
        # also check the MMC/SDIO contract before acting on such a claim.
        self.assertEqual('consistent_unverified', net['status'])
        self.assertEqual('mmc_not_ready', order['error'])

    def test_rtc_sync_must_follow_fresh_time_source(self):
        seq = ['time_source_confirmed', 'rtc_untrusted', 'sdio_quiesced',
               'suspend', 'resume', 'rtc_sync_confirmed']
        net, order = self.evaluate(seq)
        self.assertEqual('consistent_unverified', net['status'])
        self.assertEqual('time_source_missing', order['error'])
        self.assertFalse(order['rtc_verified'])

    def test_replay_does_not_open_devices_or_start_commands(self):
        seq = ['mmc_ready', 'sdio_ready', 'network_request', 'wifi_on']
        with patch('builtins.open', side_effect=AssertionError('I/O')), \
             patch('subprocess.run', side_effect=AssertionError('process')):
            net, order = self.evaluate(seq)
        self.assertEqual('consistent_unverified', net['status'])
        self.assertEqual('consistent_unverified', order['status'])


if __name__ == '__main__':
    unittest.main()
