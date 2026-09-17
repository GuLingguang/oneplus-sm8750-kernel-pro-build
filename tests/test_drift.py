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


class DriftIdentityTests(unittest.TestCase):
    def test_supplied_baseline_without_identity_is_reported(self):
        baseline = {'status': 'passed', 'identity_category': 'none',
                    'identity_available': False, 'identity_expected': True}
        candidate = {'status': 'passed', 'identity_category': 'none',
                     'identity_available': True, 'identity_expected': True}
        result = drift.profile_result('p', None, baseline, candidate)
        self.assertIn('baseline-identity-unavailable', result['classification'])

    def test_fetched_baseline_without_identity_is_not_reported(self):
        baseline = {'status': 'passed', 'identity_category': 'none',
                    'identity_available': False, 'identity_expected': False}
        candidate = {'status': 'passed', 'identity_category': 'none',
                     'identity_available': False, 'identity_expected': False}
        result = drift.profile_result('p', None, baseline, candidate)
        self.assertNotIn('baseline-identity-unavailable', result['classification'])
        self.assertNotIn('candidate-identity-unavailable', result['classification'])

    def test_archive_baseline_is_not_reported_as_a_lock_mismatch(self):
        temp_root = drift.ROOT / 'work' / '_tmp'
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as path:
            root = Path(path)
            source = root / 'source'
            (source / 'drivers').mkdir(parents=True)
            scratch = root / 'temp'
            scratch.mkdir()
            lock = {
                'sources': {'kernel': {
                    'url': 'https://example.invalid/k.git', 'reference': 'main',
                    'commit': 'a' * 40, 'directory': 'src',
                }},
                'steps': [],
            }
            result = drift.check_variant(
                {'features': {}}, lock, {'blockers': []}, source, {}, 'baseline', scratch,
            )
            self.assertFalse(result['identity_available'])
            self.assertEqual(result['identity_category'], 'none')

class DriftProviderTests(unittest.TestCase):
    def test_tracked_ref_reads_only_the_leading_token(self):
        self.assertEqual(drift.tracked_ref({'reference': 'lineage-23.2'}), 'lineage-23.2')
        self.assertEqual(
            drift.tracked_ref({'reference': 'main (candidate from historical run; not floating)'}),
            'main',
        )
        self.assertEqual(
            drift.tracked_ref({'reference': 'gki-android15-6.6 / v2.3.0'}),
            'gki-android15-6.6',
        )
        self.assertIsNone(drift.tracked_ref({'reference': ''}))
        self.assertIsNone(drift.tracked_ref({'reference': '/not/a/branch'}))

    def test_locked_provider_references_are_monitorable(self):
        for name in ('ace6-minimal-6.6', 'ace6-resukisu-susfs-inline-6.6'):
            lock = profile_rules.read_json(drift.ROOT / f'manifests/locks/{name}.lock.json')
            for source_name, source in lock['sources'].items():
                self.assertIsNotNone(
                    drift.tracked_ref(source),
                    f'{name}:{source_name} has no monitorable reference',
                )

    def test_source_branch_drift_classifies_current_drift_and_unresolved(self):
        sources = {
            'kernel': {'url': 'https://example.invalid/k.git', 'reference': 'lineage-23.2', 'commit': 'a' * 40},
            'resukisu': {'url': 'https://example.invalid/r.git', 'reference': 'main (pinned)', 'commit': 'b' * 40},
            'susfs': {'url': 'https://example.invalid/s.git', 'reference': 'gki-android15-6.6 / v2.3.0', 'commit': 'c' * 40},
            'odd': {'url': 'https://example.invalid/o.git', 'reference': '', 'commit': 'd' * 40},
        }

        def fake_remote_branch(url, branch, mirror_prefix='', timeout=0):
            if branch == 'lineage-23.2':
                return 'a' * 40
            if branch == 'main':
                return 'e' * 40
            raise RuntimeError('cannot reach host')

        original = drift.remote_branch
        drift.remote_branch = fake_remote_branch
        try:
            entries = {item['name']: item for item in drift.source_branch_drift(sources)}
        finally:
            drift.remote_branch = original

        self.assertEqual(entries['kernel']['status'], 'current')
        self.assertEqual(entries['resukisu']['status'], 'drift')
        self.assertEqual(entries['resukisu']['tracked_ref'], 'main')
        self.assertEqual(entries['resukisu']['observed_commit'], 'e' * 40)
        self.assertEqual(entries['susfs']['status'], 'unresolved')
        self.assertEqual(entries['susfs']['tracked_ref'], 'gki-android15-6.6')
        self.assertEqual(entries['odd']['status'], 'unmonitored')

    def test_profile_result_reports_provider_branch_drift(self):
        baseline = {'status': 'passed', 'identity_category': 'none'}
        candidate = {'status': 'passed', 'identity_category': 'none'}
        result = drift.profile_result('p', None, baseline, candidate, [
            {'name': 'resukisu', 'status': 'drift'},
            {'name': 'susfs', 'status': 'unresolved'},
        ])
        self.assertIn('source-branch-drift:resukisu', result['classification'])
        self.assertIn('source-status-unresolved:susfs', result['classification'])

    def test_exit_code_fails_when_ci_read_no_source(self):
        summary = {'sources': 5, 'resolved': 0, 'drift': 0, 'unresolved': 5, 'unmonitored': 0}
        self.assertEqual(drift.check_exit_code([], summary, True), 1)

    def test_exit_code_passes_when_ci_read_some_sources(self):
        summary = {'sources': 5, 'resolved': 3, 'drift': 2, 'unresolved': 2, 'unmonitored': 0}
        self.assertEqual(drift.check_exit_code([], summary, True), 0)

    def test_exit_code_ignores_unreadable_sources_outside_ci(self):
        summary = {'sources': 5, 'resolved': 0, 'drift': 0, 'unresolved': 5, 'unmonitored': 0}
        self.assertEqual(drift.check_exit_code([], summary, False), 0)

    def test_exit_code_passes_when_the_check_was_skipped(self):
        summary = {'sources': 0, 'resolved': 0, 'drift': 0, 'unresolved': 0, 'unmonitored': 0}
        self.assertEqual(drift.check_exit_code([], summary, True), 0)

    def test_exit_code_fails_on_a_failed_candidate(self):
        reports = [{'candidate': {'status': 'failed'}}]
        summary = {'sources': 1, 'resolved': 1, 'drift': 0, 'unresolved': 0, 'unmonitored': 0}
        self.assertEqual(drift.check_exit_code(reports, summary, False), 1)

    def test_missing_branch_is_unmonitored_not_unresolved(self):
        def missing(url, branch, mirror_prefix='', timeout=0):
            raise drift.BranchMissing(f'remote has no branch named: {branch}')

        original = drift.remote_branch
        drift.remote_branch = missing
        try:
            entries = drift.source_branch_drift({
                'kernel': {'url': 'https://example.invalid/k.git', 'reference': 'v1.2.3', 'commit': 'a' * 40},
            })
        finally:
            drift.remote_branch = original
        self.assertEqual(entries[0]['status'], 'unmonitored')
        self.assertIn('no branch named', entries[0]['detail'])

    def test_markdown_reports_the_source_branch_summary(self):
        report = {
            'generated_utc': '2026-09-11T00:00:00+00:00',
            'profiles': [],
            'source_branches': [
                {'name': 'kernel', 'tracked_ref': 'lineage-23.2', 'locked_commit': 'a' * 40,
                 'observed_commit': 'a' * 40, 'status': 'current'},
                {'name': 'susfs', 'tracked_ref': 'gki-android15-6.6', 'locked_commit': 'b' * 40,
                 'observed_commit': None, 'status': 'unresolved'},
            ],
            'source_branch_summary': {'sources': 2, 'resolved': 1, 'drift': 0, 'unresolved': 1, 'unmonitored': 0},
        }
        text = drift.markdown(report)
        self.assertIn('Locked source branches', text)
        self.assertIn('Read 1 of 2 sources; 1 unresolved, 0 unmonitored, 0 moved.', text)

    def test_source_branch_summary_counts_each_status(self):
        summary = drift.source_branch_summary([
            {'name': 'a', 'status': 'current'},
            {'name': 'b', 'status': 'drift'},
            {'name': 'c', 'status': 'unresolved'},
            {'name': 'd', 'status': 'unmonitored'},
        ])
        self.assertEqual(
            summary,
            {'sources': 4, 'resolved': 2, 'drift': 1, 'unresolved': 1, 'unmonitored': 1},
        )

    def test_source_branch_drift_retries_before_giving_up(self):
        calls = []

        def flaky(url, branch, mirror_prefix='', timeout=0):
            calls.append(branch)
            if len(calls) == 1:
                raise RuntimeError('transient')
            return 'a' * 40

        original = drift.remote_branch
        drift.remote_branch = flaky
        try:
            entries = drift.source_branch_drift({
                'kernel': {'url': 'https://example.invalid/k.git', 'reference': 'main', 'commit': 'a' * 40},
            })
        finally:
            drift.remote_branch = original
        self.assertEqual(len(calls), 2)
        self.assertEqual(entries[0]['status'], 'current')

