"""Suite-wide guard: a test must not leave AMIWIND_* environment variables changed (TEST-ENV-LEAK-HULL-33).

install() wraps unittest.TestCase._callSetUp so every test records the AMIWIND_* variables before its setUp and
checks them in its last cleanup, after its own patchers have stopped. A test that leaves one changed fails with the
names, and the environment is put back so the leak cannot reach the next test. The suite installs it in every
process: tests/test_env_guard.py during discovery (one-process `python -m unittest discover`) and
tools/run_tests.py in each worker.
"""
import os
import unittest

PREFIX = 'AMIWIND_'


def snapshot(environ=None):
    environ = os.environ if environ is None else environ
    return {k: v for k, v in environ.items() if k.startswith(PREFIX)}


def restore(before, environ=None):
    environ = os.environ if environ is None else environ
    for key in [k for k in environ if k.startswith(PREFIX) and k not in before]:
        del environ[key]
    environ.update(before)


def changes(before, after):
    return sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))


def _check(before):
    changed = changes(before, snapshot())
    if changed:
        restore(before)
        raise AssertionError('test left environment variables changed: %s (wrap the change in '
                             'patch.dict(os.environ); TEST-ENV-LEAK-HULL-33)' % ', '.join(changed))


# Test-run defaults, set before any test's snapshot: the suite runs builder entry points on small temporary
# workspaces, so the build preflight's free-space minimum (tools/build_preflight.py, fatal for release
# versions) must not depend on the host's disk; its own tests pass explicit minima. Origin: gate 1335, the
# first suite with VERSION 0.0.35 (a final version) stopped seven entry-point tests on 1.9 GiB free in /tmp.
SUITE_ENV = {'AMIWIND_MIN_FREE_GIB': '0'}


def install():
    """Idempotent; returns True when the guard is active."""
    for key, value in SUITE_ENV.items():
        os.environ.setdefault(key, value)
    case = unittest.TestCase
    if getattr(case, '_amiwind_env_guard', False):
        return True
    original = getattr(case, '_callSetUp', None)
    if original is None:
        return False

    def _callSetUp(self):
        self.addCleanup(_check, snapshot())
        original(self)

    case._callSetUp = _callSetUp
    case._amiwind_env_guard = True
    return True


def isolated(cls):
    """Class decorator for tests that run tools/build.py main() in-process: build.main exports its build switches
    (AMIWIND_*) for the converters it starts, so each test of the class runs inside patch.dict(os.environ)."""
    from unittest.mock import patch
    original = cls.setUp

    def setUp(self):
        guard = patch.dict(os.environ)
        guard.start()
        self.addCleanup(guard.stop)
        original(self)

    cls.setUp = setUp
    return cls
