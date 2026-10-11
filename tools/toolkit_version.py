# SPDX-License-Identifier: GPL-3.0-only
"""The Toolkit's "Last updated with AmiWind vX" line, kept honest by the release check.

Two version marks, both kept by this check. The Toolkit's own version (TOOLKIT.version in world-map.html, carried in
its exports as "toolkit_version") goes up by at least 0.0.1 in every release in which a Toolkit file changed. The line
names the AmiWind version the Toolkit (amiwind-toolkit/) last changed in. It is never
bumped just because VERSION moved: only when a Toolkit file differs from the previous release
(the published commit in tools/previous-release.json) must it name the version being released
(VERSION without its -suffix: 0.0.36-dev1 -> v0.0.36).

    python3 tools/toolkit_version.py status   what changed since the previous release, what the line says
    python3 tools/toolkit_version.py check    exit 1 when the Toolkit changed and the line is stale
    python3 tools/toolkit_version.py bump     write the expected line into header.js and index.html and raise the
                                              Toolkit's own version by 0.0.1 over the previous release's

`tools/release.py --check` runs the check. A source tree without git history, or a one-commit
(shallow) checkout as in hosted CI, cannot compare and is skipped, as in tools/previous_release.py.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from previous_release import load_pin  # noqa: E402

TOOLKIT = 'amiwind-toolkit'
HEADER = TOOLKIT + '/header.js'
INDEX = TOOLKIT + '/index.html'
HEADER_RE = re.compile(r"(const VERSION_TEXT = 'Last updated with AmiWind )v(\d+\.\d+\.\d+)(';)")
INDEX_RE = re.compile(r'(<small id="toolkit-version"[^>]*>Last updated with AmiWind )v(\d+\.\d+\.\d+)(</small>)')
WORLD_MAP = TOOLKIT + '/world-map.html'
OWN_RE = re.compile(r"(const TOOLKIT = \{name: '[^']*', version: ')(\d+\.\d+\.\d+)(')")


def own_version(text):
    """The Toolkit's own version in a world-map.html text, or None."""
    found = OWN_RE.search(text)
    return found.group(2) if found else None


def as_tuple(version):
    return tuple(int(n) for n in version.split('.'))


def previous_own_version(root=ROOT, run=None):
    """The Toolkit's own version in the previous release (None when that release has no such line)."""
    run = run or (lambda *args: subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True))
    shown = run('show', load_pin(root)['published'] + ':' + WORLD_MAP)
    return own_version(shown.stdout) if shown.returncode == 0 else None


def expected_version(root=ROOT):
    """VERSION without its pre-release suffix: the release the Toolkit's changes ship in."""
    return (Path(root) / 'VERSION').read_text(encoding='utf-8').strip().split('-')[0]


def named_versions(root=ROOT):
    """(header.js version, index.html version) as the line names them."""
    header = HEADER_RE.search((Path(root) / HEADER).read_text(encoding='utf-8'))
    index = INDEX_RE.search((Path(root) / INDEX).read_text(encoding='utf-8'))
    if not header or not index:
        raise ValueError('Toolkit header line not found in %s / %s' % (HEADER, INDEX))
    return header.group(2), index.group(2)


def changed_files(root=ROOT, run=None):
    """('no-git' | 'shallow' | 'ok', [Toolkit files that differ from the previous release])."""
    run = run or (lambda *args: subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True))
    try:
        if run('rev-parse', '--git-dir').returncode != 0:
            return 'no-git', []
    except FileNotFoundError:  # no git program at all (the gate's preflight image): nothing to compare with
        return 'no-git', []
    published = load_pin(root)['published']
    if run('cat-file', '-e', published + '^{commit}').returncode != 0:
        if run('rev-parse', '-q', '--verify', 'HEAD^').returncode != 0:
            return 'shallow', []
        raise ValueError('previous release %s is not in this clone: git fetch origin tag v%s'
                         % (published[:7], load_pin(root)['version']))
    diff = run('diff', '--name-only', published, '--', TOOLKIT)
    if diff.returncode != 0:
        raise ValueError('git diff against the previous release failed: ' + diff.stderr.strip())
    return 'ok', [line for line in diff.stdout.splitlines() if line]


def check(root=ROOT, run=None):
    """A note when skipped or fine; ValueError when the Toolkit changed and the line is stale."""
    state, changed = changed_files(root, run)
    if state != 'ok':
        return 'Toolkit version line: not checked (%s source tree)' % state
    want = expected_version(root)
    header, index = named_versions(root)
    if header != index:
        raise ValueError('Toolkit version line disagrees: header.js v%s, index.html v%s; fix: python3 tools/'
                         'toolkit_version.py bump' % (header, index))
    current = own_version((Path(root) / WORLD_MAP).read_text(encoding='utf-8'))
    previous = previous_own_version(root, run) if changed else None
    if changed and previous and (not current or as_tuple(current) <= as_tuple(previous)):
        raise ValueError('The Toolkit changed since the previous release (%d files, e.g. %s) but its own version is '
                         '%s, not above the previous release\'s %s. Fix: python3 tools/toolkit_version.py bump'
                         % (len(changed), changed[0], current, previous))
    if changed and header != want:
        raise ValueError('The Toolkit changed since the previous release (%d files, e.g. %s) but its header still '
                         'says "Last updated with AmiWind v%s"; this release is v%s. Fix: python3 tools/'
                         'toolkit_version.py bump' % (len(changed), changed[0], header, want))
    return 'Toolkit %s, version line: v%s (%s)' % (current, header, '%d Toolkit files changed since the previous '
                                                   'release' % len(changed) if changed else 'Toolkit unchanged')


def bump(root=ROOT, run=None):
    """Write the expected version into both files when the Toolkit changed; return what was done."""
    state, changed = changed_files(root, run)
    if state != 'ok':
        raise ValueError('cannot compare with the previous release (%s source tree)' % state)
    if not changed:
        return 'Toolkit unchanged since the previous release: line left as is'
    want = expected_version(root)
    for name, pattern in ((HEADER, HEADER_RE), (INDEX, INDEX_RE)):
        path = Path(root) / name
        text = path.read_text(encoding='utf-8')
        path.write_text(pattern.sub(lambda m: m.group(1) + 'v' + want + m.group(3), text, count=1),
                        encoding='utf-8', newline='\n')
    done = ['header set to "Last updated with AmiWind v%s"' % want]
    world = Path(root) / WORLD_MAP
    text = world.read_text(encoding='utf-8')
    current, previous = own_version(text), previous_own_version(root, run)
    if current and previous and as_tuple(current) <= as_tuple(previous):
        major, minor, patch = as_tuple(previous)
        raised = '%d.%d.%d' % (major, minor, patch + 1)
        world.write_text(OWN_RE.sub(lambda m: m.group(1) + raised + m.group(3), text, count=1),
                         encoding='utf-8', newline='\n')
        done.append('own version %s -> %s' % (current, raised))
    return 'Toolkit ' + '; '.join(done)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=('status', 'check', 'bump'))
    args = ap.parse_args(argv)
    try:
        if args.command == 'status':
            state, changed = changed_files()
            print('previous release: v%s (%s), comparison: %s' % (load_pin()['version'], load_pin()['published'][:7], state))
            print('header names: v%s / v%s, this release: v%s' % (*named_versions(), expected_version()))
            print('Toolkit own version: %s (previous release: %s)' % (
                own_version((ROOT / WORLD_MAP).read_text(encoding='utf-8')), previous_own_version()))
            for name in changed:
                print('  changed: ' + name)
        else:
            print(check() if args.command == 'check' else bump())
    except ValueError as exc:
        ap.exit(1, 'Error: %s\n' % exc)
    return 0


if __name__ == '__main__':
    sys.exit(main())
