from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import drift
import profile as profile_rules


class DriftSourceTests(unittest.TestCase):
    def test_apply_patch_targets_snapshot_inside_parent_repository(self):
        temp_root = drift.ROOT / 'work' / '_tmp'
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as path:
            root = Path(path)
            kernel = root / 'src'
            kernel.mkdir()
            patch = root / 'new.patch'
            patch.write_text(
                'diff --git a/drift-regression.txt b/drift-regression.txt\n'
                'new file mode 100644\n'
                'index 0000000..257cc56\n'
                '--- /dev/null\n'
                '+++ b/drift-regression.txt\n'
                '@@ -0,0 +1 @@\n'
                '+snapshot target\n'
            )
            code, output = drift.apply_patch(kernel, patch, check=True)
            self.assertEqual(code, 0, output)
            code, output = drift.apply_patch(kernel, patch)
            self.assertEqual(code, 0, output)
            self.assertEqual((kernel / 'drift-regression.txt').read_text(), 'snapshot target\n')

    def test_git_root_does_not_accept_parent_repository(self):
        temp_root = drift.ROOT / 'work' / '_tmp'
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as path:
            self.assertIsNone(drift.git_root(Path(path)))
            self.assertIsNone(drift.source_identity(Path(path))['sha'])

    def test_collect_source_specs_includes_optional_profile_sources(self):
        minimal = profile_rules.read_json(
            drift.ROOT / 'manifests/locks/ace6-minimal-6.6.lock.json'
        )
        manual = profile_rules.read_json(
            drift.ROOT / 'manifests/locks/ace6-resukisu-manual-6.6.lock.json'
        )
        specs = drift.collect_source_specs([
            ('minimal', None, minimal, None),
            ('manual', None, manual, None),
        ])
        self.assertIn('resukisu', specs)
        self.assertEqual(specs['kernel'], minimal['sources']['kernel'])

    def test_collect_source_specs_rejects_conflicting_definitions(self):
        minimal = profile_rules.read_json(
            drift.ROOT / 'manifests/locks/ace6-minimal-6.6.lock.json'
        )
        changed = dict(minimal)
        changed['sources'] = dict(minimal['sources'])
        changed['sources']['kernel'] = dict(minimal['sources']['kernel'])
        changed['sources']['kernel']['commit'] = '0' * 40
        with self.assertRaisesRegex(RuntimeError, 'source lock differs'):
            drift.collect_source_specs([
                ('first', None, minimal, None),
                ('second', None, changed, None),
            ])
