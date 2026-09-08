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
