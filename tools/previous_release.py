#!/usr/bin/env python3
"""Release ancestry check: a release candidate or final must contain the previous release.

tools/previous-release.json pins the previous release: its version and the commits that carry its
source (the release line's head and, once published, the tagged commit). A release candidate or final
whose HEAD has none of them as an ancestor is refused, so no fix that shipped in the previous release
can be missing from the next one (RELEASE-PREVIOUS-FIXES-MISSING-33).

When the pin names a "published" commit (the vX tag's commit on the public repository), that commit is
required: a private release-line commit with the same tree only counts once the published commit is an
ancestor too, and the refusal prints the exact fix (`git merge -s ours --no-edit <published>` when the
release's content is already in, `git merge <published>` otherwise). Run it first: when a release branch
is created and before any stage of an rc/final build (tools/build.py does).

Development versions (-dev, -devN) only report the result. A source tree without git history (a
source archive) cannot be checked; builds then print a note and the release gate checks the
repository instead.

    python3 tools/previous_release.py check [--repo DIR] [--version VERSION]
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = 'tools/previous-release.json'


def load_pin(root=ROOT):
    pin = json.loads((Path(root) / PIN).read_text(encoding='utf-8'))
    commits = pin.get('commits')
    if not pin.get('version') or not isinstance(commits, list) or not commits:
        raise ValueError(f'{PIN}: needs "version" and a non-empty "commits" list')
    for c in commits + ([pin['published']] if 'published' in pin else []):
        if not re.fullmatch(r'[0-9a-f]{7,40}', str(c)):
            raise ValueError(f'{PIN}: {c!r} is not a commit id')
    return pin


def is_release_version(version):
    """rc and final versions are releases; -dev and -devN are not."""
    return not re.search(r'-dev[0-9]*$', version.strip())


def git_runner(root):
    def git(*args):
        return subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True).returncode
    return git


def ancestry(root, git=None):
    """'no-git' | ('ok', commit) | ('missing', reason). git(*args) returns an exit code."""
    git = git or git_runner(root)
    try:
        if git('rev-parse', '--git-dir') != 0:
            return 'no-git', None
    except OSError:
        return 'no-git', None
    pin = load_pin(root)
    published = pin.get('published')
    if published:
        contained = [c for c in pin['commits'] if git('cat-file', '-e', f'{c}^{{commit}}') == 0
                     and git('merge-base', '--is-ancestor', c, 'HEAD') == 0]
        fix = (f'git merge -s ours --no-edit {published[:7]}' if contained
               else f'git merge {published[:7]}')
        if git('cat-file', '-e', f'{published}^{{commit}}') != 0:
            return 'missing', (f'the published v{pin["version"]} commit {published[:7]} is not in this repository; '
                               f'fix: git fetch origin tag v{pin["version"]}, then {fix}')
        if git('merge-base', '--is-ancestor', published, 'HEAD') == 0:
            return 'ok', published
        return 'missing', (f'HEAD does not contain the published v{pin["version"]} commit {published[:7]}'
                           + (f' (it contains the private release-line commit {contained[0][:7]} with the '
                              f'same tree)' if contained else '') + f'; fix: {fix}')
    known = [c for c in pin['commits'] if git('cat-file', '-e', f'{c}^{{commit}}') == 0]
    for c in known:
        if git('merge-base', '--is-ancestor', c, 'HEAD') == 0:
            return 'ok', c
    if not known:
        return 'missing', (f'none of the pinned v{pin["version"]} commits ({", ".join(pin["commits"])}) '
                           f'exists in this repository')
    return 'missing', (f'HEAD does not contain the previous release v{pin["version"]} '
                       f'(pinned {", ".join(known)}): merge it first')


def require_previous_release(root, version, git=None):
    """Raise ValueError for a release version whose HEAD lacks the previous release; return a note or None."""
    state, detail = ancestry(root, git)
    if state == 'ok':
        return None
    if state == 'no-git':
        return 'Note: no git history in this source tree; the previous-release ancestry check is left to the release gate.'
    if is_release_version(version):
        raise ValueError(f'Version {version} is a release candidate or final, and {detail}')
    return f'Note: {detail} (development version {version}: not refused)'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('check')
    c.add_argument('--repo', type=Path, default=ROOT)
    c.add_argument('--version')
    args = ap.parse_args(argv)
    version = args.version or (args.repo / 'VERSION').read_text(encoding='utf-8').strip()
    try:
        note = require_previous_release(args.repo, version)
    except ValueError as exc:
        print(f'previous-release: REFUSED: {exc}')
        return 1
    print(f'previous-release: ok ({version})' + (f'; {note}' if note else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
