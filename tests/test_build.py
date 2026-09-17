import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build


class CommandTimeoutTests(unittest.TestCase):
    def test_timeout_kills_descendants_after_parent_exits(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / 'marker'
            script = (
                "(trap '' TERM; while :; do date +%s%N > \"$1\"; sleep 0.05; done) & "
                "child=$!; trap 'exit 0' TERM; wait \"$child\""
            )
            with self.assertRaisesRegex(build.BuildError, r'timed out after 1s'):
                build.run_command(
                    ['bash', '-c', script, 'timeout-test', str(marker)],
                    timeout=1,
                )
            self.assertTrue(marker.exists())
            before = marker.read_text()
            time.sleep(0.2)
            self.assertEqual(marker.read_text(), before)

    def test_timeout_environment_requires_positive_integer(self):
        with patch.dict(os.environ, {'ACE6_BUILD_TIMEOUT_SECONDS': '0'}):
            with self.assertRaisesRegex(build.BuildError, 'positive integer'):
                build.build_timeout_seconds()


class BuildTimestampTests(unittest.TestCase):
    def make_repo(self, root, epoch):
        repo = Path(root) / 'kernel'
        repo.mkdir()
        for argv in (
            ['git', 'init', '--quiet'],
            ['git', 'config', 'user.email', 'test@example.invalid'],
            ['git', 'config', 'user.name', 'test'],
        ):
            build.run_command(argv, cwd=repo)
        (repo / 'Makefile').write_text('x\n')
        build.run_command(['git', 'add', 'Makefile'], cwd=repo)
        env = dict(os.environ)
        env.update({'GIT_AUTHOR_DATE': f'{epoch} +0000', 'GIT_COMMITTER_DATE': f'{epoch} +0000'})
        build.run_command(['git', 'commit', '--quiet', '-m', 'seed'], cwd=repo, env=env)
        return repo

    def test_explicit_build_time_is_used_verbatim(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self.make_repo(tmp, 1700000000)
            stamp, source, epoch = build.reproducible_build_timestamp(repo, {'build_time': '2025-05-25 00:00:00'})
            self.assertEqual(stamp, '2025-05-25 00:00:00')
            self.assertEqual(source, 'explicit')
            self.assertEqual(epoch, 1700000000)

    def test_empty_build_time_derives_from_the_locked_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self.make_repo(tmp, 1700000000)
            stamp, source, epoch = build.reproducible_build_timestamp(repo, {'build_time': ''})
            self.assertEqual(source, 'locked-commit-date')
            self.assertEqual(stamp, 'Tue Nov 14 22:13:20 UTC 2023')
            self.assertEqual(epoch, 1700000000)

    def test_literal_n_is_treated_as_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self.make_repo(tmp, 1700000000)
            self.assertEqual(
                build.reproducible_build_timestamp(repo, {'build_time': 'N'}),
                build.reproducible_build_timestamp(repo, {'build_time': ''}),
            )

    def test_derived_stamp_does_not_depend_on_the_host_timezone(self):
        # Setting TZ alone changes nothing: CPython reads the C library zone, so
        # the test must call tzset() or it passes even against an implementation
        # that uses naive local time.
        with tempfile.TemporaryDirectory() as tmp:
            repo = self.make_repo(tmp, 1700000000)
            original = os.environ.get('TZ')
            try:
                os.environ['TZ'] = 'Asia/Shanghai'
                time.tzset()
                first = build.reproducible_build_timestamp(repo, {'build_time': ''})
                os.environ['TZ'] = 'America/New_York'
                time.tzset()
                second = build.reproducible_build_timestamp(repo, {'build_time': ''})
            finally:
                if original is None:
                    os.environ.pop('TZ', None)
                else:
                    os.environ['TZ'] = original
                time.tzset()
            self.assertEqual(first[0], second[0])
            self.assertEqual(first[0], 'Tue Nov 14 22:13:20 UTC 2023')

    def test_missing_repository_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(build.BuildError, 'reproducible timestamp'):
                build.reproducible_build_timestamp(Path(tmp), {'build_time': ''})
