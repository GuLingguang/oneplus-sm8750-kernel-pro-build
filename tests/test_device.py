"""Device acceptance collector: parsers, evidence shape, and hard gates.

Run: python3 -m unittest discover -s tests -v
No network, toolchain, device, or third-party Python dependency required: the
adb boundary is replaced by a fake runner, so the whole collector is exercised
without a phone attached.
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import device as d


GETPROP = """[ro.product.model]: [PLQ110]
[ro.product.device]: [OP6113L1]
[ro.product.vendor.device]: [ktm]
[ro.build.version.release]: [16]
[ro.boot.slot_suffix]: [_a]
[sys.boot_completed]: [1]
"""

PROC_VERSION = ("Linux version 6.6.142-4k-gcb967c26c2c5+ (build@host) "
                "(Android clang) #1 SMP PREEMPT Tue Aug 18 16:57:28 UTC 2026\n")

CONFIG = """#
CONFIG_KSU=y
CONFIG_KSU_SUSFS=y
CONFIG_KSU_SUSFS_SPOOF_UNAME=y
CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG=y
CONFIG_SOMETHING_ELSE=y
"""

BATTERY = """Current Battery Service state:
  AC powered: false
  level: 99
  health: 2
  temperature: 332
"""


class ParserTests(unittest.TestCase):
    def test_getprop_pairs(self):
        props = d.parse_getprop(GETPROP)
        self.assertEqual(props['ro.product.model'], 'PLQ110')
        self.assertEqual(props['sys.boot_completed'], '1')
        self.assertEqual(props['ro.boot.slot_suffix'], '_a')

    def test_kernel_release(self):
        self.assertEqual(d.kernel_release(PROC_VERSION), '6.6.142-4k-gcb967c26c2c5+')
        self.assertEqual(d.kernel_release(''), d.UNAVAILABLE)

    def test_config_keeps_only_ksu_keys_and_reports_missing_ones(self):
        config = d.parse_config(CONFIG)
        self.assertEqual(config['CONFIG_KSU'], 'y')
        self.assertEqual(config['CONFIG_KSU_SUSFS_SPOOF_UNAME'], 'y')
        self.assertNotIn('CONFIG_SOMETHING_ELSE', config)
        self.assertEqual(len(config), 4)

    def test_panic_matching_ignores_ordinary_lines(self):
        self.assertEqual(d.panic_matches('everything is fine'), [])
        self.assertEqual(len(d.panic_matches('Kernel panic - not syncing: x')), 1)
        self.assertEqual(len(d.panic_matches('Internal error: Oops: 96000005')), 1)

    def test_battery_is_labelled_lines(self):
        battery = d.parse_battery(BATTERY)
        self.assertEqual(battery['capacity_percent'], '99')
        self.assertEqual(battery['temperature_c'], '332')

    def test_zram_swap_needs_the_swap_table(self):
        table = "Filename\t\t\t\tType\t\tSize\t\tUsed\t\tPriority\n/dev/zram0   partition   6291456 1   100\n"
        zram = d.parse_zram('6442450944', 'lzo-rle', table)
        self.assertTrue(zram['swap_active'])
        self.assertEqual(zram['algorithm'], 'lzo-rle')
        self.assertFalse(d.parse_zram('1', 'lzo', '')['swap_active'])


def fake_device(overrides=None):
    """A runner that answers the collector's questions like a booted phone."""
    answers = {
        'getprop': GETPROP,
        'getprop sys.boot_completed': '1',
        'cat /proc/version': PROC_VERSION,
        'uname -r': '6.6.89-android15-8-g7e1f3c083cc6-abogki467167594-4k',
        'id': 'uid=0(root) gid=0(root) context=u:r:ksu:s0',
        'zcat /proc/config.gz': CONFIG,
        'ksud --version': '4.1.0-1338-g058cdc93 (uapi: 2)',
        'cat /sys/block/zram0/disksize': '6442450944',
        'cat /sys/block/zram0/comp_algorithm': 'lzo-rle',
        'cat /proc/swaps': '/dev/zram0 partition 6291456 1 100',
        'dumpsys battery': BATTERY,
        'dmesg | tail -n 200': 'nothing alarming here',
    }
    answers.update(overrides or {})

    def run(args, timeout=30):
        command = args[-1] if args and args[0] == 'shell' else ' '.join(args)
        return answers.get(command, '')

    return run


PROFILE = {
    'name': 'ace6-minimal-6.6',
    'config_id': 'x' * 64,
    'lock_id': 'y' * 64,
    'kernel_release': '6.6.142-4k-gcb967c26c2c5+',
    'image_sha256': 'z' * 64,
    'artifact': 'Kernel-Ace6-Lingguang-20260818.zip',
    'artifact_sha256': 'w' * 64,
}

RECORDED_SHAPE = json.loads(
    (d.ROOT / 'docs/evidence/t26-runtime.json').read_text()
)


class EvidenceTests(unittest.TestCase):
    def test_shape_matches_the_recorded_t26_evidence(self):
        evidence = d.build_evidence(fake_device(), PROFILE, soak_seconds=0, interval=1)
        self.assertEqual(set(evidence), set(RECORDED_SHAPE))
        self.assertEqual(set(evidence['status']), set(RECORDED_SHAPE['status']))
        self.assertEqual(set(evidence['device']), set(RECORDED_SHAPE['device']))
        self.assertEqual(set(evidence['observations']), set(RECORDED_SHAPE['observations']))
        self.assertEqual(evidence['status']['release_allowed'], False)
        self.assertEqual(evidence['status']['runtime'], 'partial-pass')

    def test_observations_come_from_the_device(self):
        evidence = d.build_evidence(fake_device(), PROFILE, soak_seconds=0, interval=1)
        observations = evidence['observations']
        self.assertTrue(observations['root_adbd'])
        self.assertEqual(observations['proc_version_release'], PROFILE['kernel_release'])
        self.assertTrue(observations['kernel_banner_matches_artifact'])
        self.assertTrue(observations['spoof_uname_observed'])
        self.assertEqual(observations['embedded_config']['CONFIG_KSU_SUSFS'], 'y')

    def test_a_device_that_has_not_booted_is_a_hard_failure(self):
        run = fake_device({'getprop sys.boot_completed': '0'})
        with self.assertRaises(d.DeviceError):
            d.build_evidence(run, PROFILE, soak_seconds=0, interval=1)

    def test_a_panic_in_the_kernel_log_is_a_hard_failure(self):
        run = fake_device({'dmesg | tail -n 200': 'Kernel panic - not syncing: oops'})
        with self.assertRaises(d.DeviceError):
            d.build_evidence(run, PROFILE, soak_seconds=0, interval=1)

    def test_soak_counts_its_samples(self):
        stability = d.soak(fake_device(), seconds=2, interval=1)
        self.assertGreaterEqual(stability['samples'], 2)
        self.assertTrue(stability['boot_completed_stable'])
        self.assertTrue(stability['kernel_release_stable'])
        self.assertFalse(stability['panic_or_oops_match'])

    def test_unanswered_questions_are_recorded_not_invented(self):
        evidence = d.build_evidence(fake_device(), PROFILE, soak_seconds=0, interval=1)
        self.assertEqual(evidence['smoke_tests']['wifi'], d.UNAVAILABLE)


class BuildOutTests(unittest.TestCase):
    def test_reads_profile_and_artifact_from_a_build_output(self):
        manifest = {
            'profile': 'ace6-minimal-6.6',
            'config_id': 'a' * 64,
            'lock_id': 'b' * 64,
            'build': {'kernel_release': '6.6.142-4k-gcb967c26c2c5+',
                      'image': {'sha256': 'c' * 64}},
            'resolved': {'kernel_localversion': '-4k-gcb967c26c2c5'},
            'artifacts': [{'kind': 'ak3', 'path': 'Kernel-x.zip', 'sha256': 'd' * 64}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'build-manifest.json'
            path.write_text(json.dumps(manifest))
            profile = d.read_build_out(Path(tmp))
        self.assertEqual(profile['name'], 'ace6-minimal-6.6')
        self.assertEqual(profile['artifact_sha256'], 'd' * 64)
        self.assertEqual(profile['kernel_release'], '6.6.142-4k-gcb967c26c2c5+')

    def test_a_directory_without_a_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(d.DeviceError):
                d.read_build_out(Path(tmp))


class CliTests(unittest.TestCase):
    def test_dry_run_contacts_nothing_and_succeeds(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            self.assertEqual(d.main(['--dry-run']), 0)
        self.assertIn('no device is contacted', buffer.getvalue())
        self.assertIn('adb shell getprop', buffer.getvalue())

    def test_a_real_run_needs_a_build_output(self):
        with self.assertRaises(d.DeviceError):
            d.main([])


if __name__ == '__main__':
    unittest.main()
