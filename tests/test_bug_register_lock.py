# SPDX-License-Identifier: GPL-3.0-only
"""Several register writers at once in one checkout keep every change (REGISTER-CONCURRENT-WRITE-LOST-67).

tools/bug_register.py runs every command under the register lock of its checkout, writes bugs.json by compare-and-swap
(a register that changed after it was read is read again, never written from the old copy), lets a caller hold the
lock across several commands (`lock --hold` and its token), and `check` refuses a report page whose entry is missing.

Each test runs the tool in processes of their own, as several jobs do when they file at once, on a small checkout of
its own: a copy of the tool, the families, the frames of the generated pages and a register of a few entries.
BUG_REGISTER_TOOL_UNDER_TEST names another copy of the tool to run them on (default: this checkout's own), so it can be
shown that a test fails on an older tool.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import bug_register as R  # noqa: E402
import release  # noqa: E402

TOOL = Path(os.environ.get('BUG_REGISTER_TOOL_UNDER_TEST') or ROOT / 'tools' / 'bug_register.py')
ENV = {k: v for k, v in os.environ.items() if k not in (R.LOCK_TOKEN_ENV, R.LOCK_WAIT_ENV)}
ENV.update(PYTHONPATH=os.pathsep.join([str(ROOT / 'src'), str(ROOT / 'tools')]), PYTHONDONTWRITEBYTECODE='1')
COMMIT = '0123456789abcdef0123456789abcdef01234567'

# A writer that reads the register, then waits before it writes (the time a real command spends rendering every page),
# and one that, right after its read, has the file changed under it by a writer that takes no lock.
SLOW_READER = r'''
import sys, time
from pathlib import Path
root = Path(sys.argv[1])
sys.path.insert(0, str(root / 'tools'))
import bug_register as R
real = R.load
def load(*a, **kw):
    bugs = real(*a, **kw)
    (root.parent / 'has-read').write_text('yes', encoding='utf-8')
    time.sleep(float(sys.argv[2]))
    return bugs
R.load = load
sys.exit(R.main(sys.argv[3:]))
'''
CHANGED_UNDER = r'''
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
sys.path.insert(0, str(root / 'tools'))
import bug_register as R
real, done = R.load, []
def load(*a, **kw):
    bugs = real(*a, **kw)
    if not done:
        done.append(1)
        data = root / 'docs' / 'bugs' / 'bugs.json'
        rows = json.loads(data.read_text(encoding='utf-8')) + [json.loads(sys.argv[2])]
        data.write_text(R.live_text(rows), encoding='utf-8', newline='\n')
    return bugs
R.load = load
sys.exit(R.main(sys.argv[3:]))
'''


def checkout(tmp):
    """A small checkout of the register: the tool under test, an empty register and the frames it renders into."""
    root = Path(tmp) / 'checkout'
    (root / 'tools').mkdir(parents=True)
    (root / 'docs' / 'bugs').mkdir(parents=True)
    shutil.copyfile(str(TOOL), str(root / 'tools' / 'bug_register.py'))
    for name in ('VERSION', 'CHIM_VERSION'):
        shutil.copyfile(str(ROOT / name), str(root / name))
    shutil.copyfile(str(ROOT / 'docs' / 'bugs' / 'families.json'), str(root / 'docs' / 'bugs' / 'families.json'))
    (root / 'docs' / 'BUGS.md').write_text('# Bugs\n\n%s\n%s\n' % (R.BEGIN, R.END), encoding='utf-8')
    (root / 'docs' / 'bugs' / 'README.md').write_text('# Bug reports\n\n%s\n%s\n' % (R.FAM_BEGIN, R.FAM_END),
                                                      encoding='utf-8')
    (root / 'docs' / 'bugs' / 'bugs.json').write_text('[]\n', encoding='utf-8')
    (root / 'tools' / 'release-files.json').write_text(json.dumps(
        ['docs/BUGS.md', 'docs/bugs/CHIM_TRACKER.md', 'docs/bugs/README.md', 'docs/bugs/bugs.json',
         'docs/bugs/families.json'], indent=2) + '\n', encoding='utf-8')
    return root


def add(bug_id, title):
    return ['add', bug_id, '--title', title, '--found', 'v0.0.69-dev5', '--reported-by', 'test',
            '--where', 'the register tool on a test checkout', '--severity', 'low',
            '--severity-reason', 'a test entry', '--family', 'tracker-tooling', '--build-name', 'source',
            '--source-commit', COMMIT]


def run(root, args, **env):
    return subprocess.run([sys.executable, '-B', str(root / 'tools' / 'bug_register.py')] + list(args), cwd=str(root),
                          env=dict(ENV, **env), capture_output=True, text=True, encoding='utf-8', errors='replace',
                          timeout=300)


def ids(root):
    return [b['id'] for b in json.loads((root / 'docs' / 'bugs' / 'bugs.json').read_text(encoding='utf-8'))]


def wait_for(path, seconds=120):
    end = time.monotonic() + seconds
    while not path.exists():
        if time.monotonic() > end:
            raise AssertionError('%s did not appear in %d s' % (path, seconds))
        time.sleep(0.05)


class RegisterLockTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = checkout(self.tmp.name)
        r = run(self.root, add('TEST-LOCK-SEED-69', 'A seed entry of the register about lanterns on the dock'))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def tearDown(self):
        self.tmp.cleanup()

    def test_two_writers_at_once_keep_both_entries(self):
        # the first writer reads the register and works for 3 s before it writes; the second starts while it works
        first = subprocess.Popen([sys.executable, '-B', '-c', SLOW_READER, str(self.root), '3'] +
                                 add('TEST-LOCK-FIRST-69', 'The first writer files an entry about the harbour bell'),
                                 cwd=str(self.root), env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, encoding='utf-8', errors='replace')
        try:
            wait_for(self.root.parent / 'has-read')
            second = run(self.root, add('TEST-LOCK-SECOND-69', 'The second writer files an entry about a cellar door'))
            out = first.communicate(timeout=300)[0]
        finally:
            if first.poll() is None:
                first.kill()
                first.wait()
        self.assertEqual(first.returncode, 0, out)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(sorted(ids(self.root)), ['TEST-LOCK-FIRST-69', 'TEST-LOCK-SECOND-69', 'TEST-LOCK-SEED-69'],
                         'an entry was lost: the later writer saved the register from a copy read before the '
                         'earlier write')
        self.assertIn('waiting for it', second.stderr, 'the second writer did not wait for the lock')
        self.assertEqual(run(self.root, ['check']).returncode, 0)

    def test_a_register_changed_after_its_read_is_read_again(self):
        # a writer that takes no lock changes bugs.json between this command's read and its write
        seed = json.loads((self.root / 'docs' / 'bugs' / 'bugs.json').read_text(encoding='utf-8'))[0]
        other = dict(seed, id='TEST-LOCK-OTHER-69', title='An entry written by a writer that takes no lock',
                     report=None)
        r = subprocess.run([sys.executable, '-B', '-c', CHANGED_UNDER, str(self.root), json.dumps(other)] +
                           add('TEST-LOCK-MINE-69', 'This command adds an entry about the ferry timetable'),
                           cwd=str(self.root), env=ENV, capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=300)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(sorted(ids(self.root)), ['TEST-LOCK-MINE-69', 'TEST-LOCK-OTHER-69', 'TEST-LOCK-SEED-69'],
                         'the register was written from the copy read before the other writer\'s change')
        self.assertIn('changed on disk after it was read', r.stderr)
        self.assertEqual(run(self.root, ['check']).returncode, 0)

    def test_check_refuses_a_page_without_its_entry(self):
        self.assertEqual(run(self.root, ['check']).returncode, 0)
        (self.root / 'docs' / 'bugs' / 'TEST-LOST-ROW-69.md').write_text(
            '# TEST-LOST-ROW-69: a page whose entry was lost\n', encoding='utf-8')
        r = run(self.root, ['check'])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn('docs/bugs/TEST-LOST-ROW-69.md: a report page without a register entry', r.stderr)

    def test_a_held_lock_covers_its_token_and_holds_everyone_else(self):
        with subprocess.Popen([sys.executable, '-B', str(self.root / 'tools' / 'bug_register.py'), 'lock', '--hold',
                               '--max-seconds', '240'], cwd=str(self.root), env=ENV, stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8',
                              errors='replace') as holder:
            self.held_lock(holder)
        self.assertIn('free', run(self.root, ['lock', '--status']).stdout)
        r = run(self.root, add('TEST-LOCK-OUTSIDE-69', 'A command outside the held lock about a dry well'))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('TEST-LOCK-OUTSIDE-69', ids(self.root))

    def held_lock(self, holder):
        try:
            first = holder.stdout.readline().split()
            self.assertEqual(first[:1], ['LOCKED'], first)
            token = first[1]
            r = run(self.root, add('TEST-LOCK-UNDER-69', 'A command run under the held lock about a rope bridge'),
                    **{R.LOCK_TOKEN_ENV: token})
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertNotIn('waiting for it', r.stderr)
            status = run(self.root, ['lock', '--status'])
            self.assertIn('the register lock is held', status.stdout)
            self.assertIn('lock --hold', status.stdout)
            before = (self.root / 'docs' / 'bugs' / 'bugs.json').read_bytes()
            r = run(self.root, add('TEST-LOCK-OUTSIDE-69', 'A command outside the held lock about a dry well'),
                    **{R.LOCK_WAIT_ENV: '1'})
            self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
            self.assertIn('REFUSED', r.stderr)
            self.assertEqual((self.root / 'docs' / 'bugs' / 'bugs.json').read_bytes(), before, 'written while held')
            r = run(self.root, add('TEST-LOCK-OUTSIDE-69', 'A command outside the held lock about a dry well'),
                    **{R.LOCK_TOKEN_ENV: 'not-the-token', R.LOCK_WAIT_ENV: '1'})
            self.assertEqual(r.returncode, 3, 'a wrong token ran under the lock')
            holder.stdin.close()
            self.assertEqual(holder.wait(timeout=60), 0)
            self.assertIn('RELEASED', holder.stdout.read())
        finally:
            if holder.poll() is None:
                holder.kill()
                holder.wait()

    def test_writes_leave_no_temporary_files_and_the_lock_folder_is_ignored(self):
        for i, title in enumerate(('A third entry about a broken oar', 'A fourth entry about the stairs')):
            self.assertEqual(run(self.root, add('TEST-LOCK-MORE%d-69' % i, title)).returncode, 0)
        left = sorted(p.name for p in (self.root / R.LOCK_FOLDER).iterdir())
        self.assertEqual(left, [R.LOCK_NAME], 'temporary files left behind')
        self.assertEqual([p.name for p in (self.root / 'docs' / 'bugs').iterdir() if p.name.endswith('.tmp')], [])
        self.assertIn(R.LOCK_FOLDER, release.IGNORED_PARTS)
        self.assertIn('/%s/' % R.LOCK_FOLDER, (ROOT / '.gitignore').read_text(encoding='utf-8').splitlines())

    def test_a_checkout_without_a_lock_runs_check_without_it(self):
        lock = self.root / R.LOCK_FOLDER / R.LOCK_NAME
        if lock.exists():
            lock.replace(self.root / R.LOCK_FOLDER / 'moved-aside')
        lock.mkdir()          # the lock file cannot be opened: as on a read-only copy of a checkout
        r = run(self.root, ['check'])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == '__main__':
    unittest.main()
