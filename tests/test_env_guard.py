import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_guard  # noqa: E402

env_guard.install()


class EnvGuardTests(unittest.TestCase):
    def test_installed(self):
        self.assertTrue(env_guard.install())
        self.assertTrue(unittest.TestCase._amiwind_env_guard)

    def test_suite_does_not_depend_on_host_free_space(self):
        # Builder entry-point tests on temporary workspaces: no free-space minimum (gate 1335).
        self.assertEqual(os.environ.get('AMIWIND_MIN_FREE_GIB'), '0')

    def test_leaking_test_fails_and_environment_is_restored(self):
        key = 'AMIWIND_ENV_GUARD_PROBE'

        class Leaky(unittest.TestCase):
            def test_leak(self):
                os.environ[key] = '1'

            def test_clean(self):
                with patch.dict(os.environ, {key: '1'}):
                    pass

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(key, None)
            result = unittest.TestResult()
            Leaky('test_leak').run(result)
            self.assertNotIn(key, os.environ)
            self.assertEqual(len(result.errors) + len(result.failures), 1)
            self.assertIn(key, (result.errors + result.failures)[0][1])
            result = unittest.TestResult()
            Leaky('test_clean').run(result)
            self.assertTrue(result.wasSuccessful())

    def test_changes_and_restore(self):
        env = {'AMIWIND_A': '1', 'PATH': 'x'}
        before = env_guard.snapshot(env)
        env['AMIWIND_A'] = '2'
        env['AMIWIND_B'] = '3'
        self.assertEqual(env_guard.changes(before, env_guard.snapshot(env)), ['AMIWIND_A', 'AMIWIND_B'])
        env_guard.restore(before, env)
        self.assertEqual(env, {'AMIWIND_A': '1', 'PATH': 'x'})


if __name__ == '__main__':
    unittest.main()
