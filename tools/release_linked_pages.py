# SPDX-License-Identifier: GPL-3.0-only
"""Every docs page the release notes or the CHANGELOG entry of the current VERSION link must be current, not only dated.

RELEASE-LINKED-PAGES-CURRENT-64: a page's "Last updated with AmiWind vX" line was bumped for a version while nothing else on
it changed, and its generated part had fallen behind (the CHIM Progress Tracker page, PROGRESS-TRACKER-STALE-64). Two
rules, both part of the release flow:

  * a linked page whose last-updated line changed in this version while nothing else on it changed is listed for the docs
    reviewer (`list`): the date alone proves nothing;
  * when such a page has a generated block, the block must equal a fresh render: `check` refuses it (the registered check
    of the page's generator runs; a page with a generated block and no registered check is listed as unchecked).

The diff of the pages against the version's base comes from the pregate (git does not run in this container):
PAGE_DIFFS = a JSON object {page: the page's `git diff -U0` text against the merge base with the integration line}.

  python3 tools/release_linked_pages.py list     the linked pages, bump-only ones marked (for the docs reviewer)
  python3 tools/release_linked_pages.py check    exit 1 when a bump-only linked page has a stale generated block
"""
import json
import os
import posixpath
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r'\]\(\s*<?([^)#\s>]+\.md)(?:#[^)\s]*)?>?\s*(?:"[^"]*")?\)')
UPDATED = re.compile(r'^_Last updated with AmiWind v[0-9][^ ]* \(')
GENERATED = re.compile(r'<!--[^>]*GENERATED|<!--[^>]*Generated (?:whole )?by|^_Generated from', re.I | re.M)
# the check that proves a page's generated part equals a fresh render: argv after python3, run from the repository root
REGISTRY = {
    'docs/chim/PROGRESS_TRACKER.md': ['tools/cell_progress_state.py', 'check'],
    'docs/MWSCRIPT_FEATURES.md': ['tools/mwscript_features.py', 'check'],
    'docs/DIALOGUE_FEATURES.md': ['tools/dialogue_features.py', 'check'],
    'docs/BUGS.md': ['tools/bug_register.py', 'check'],
    'docs/GAME_FEATURES.md': ['-m', 'unittest', 'tests.test_game_features'],
    'docs/chim/FEATURES.md': ['-m', 'unittest', 'tests.test_chim_features'],
}


def version_of(root=ROOT):
    return (Path(root) / 'VERSION').read_text(encoding='utf-8').strip()


def links_in(text, base_dir):
    """Repository-relative .md pages linked by relative links of a text (anchors and external links dropped)."""
    out = set()
    for target in LINK.findall(text):
        if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', target):
            continue
        out.add(posixpath.normpath(posixpath.join(base_dir, target)))
    return out


def changelog_entry(text, version):
    """The CHANGELOG text of one version: from the heading naming it to the next heading of the same level."""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        m = re.match(r'^(#{1,4})\s.*\bv%s\b(?!\.\d)(?!-)' % re.escape(version), ln)
        if m:
            level = len(m.group(1))
            end = next((j for j in range(i + 1, len(lines)) if re.match(r'^#{1,%d}\s' % level, lines[j])), len(lines))
            return '\n'.join(lines[i:end])
    return ''


def linked_pages(root, version):
    root = Path(root)
    found = set()
    notes = root / 'docs' / 'releases' / 'notes' / ('RELEASE-v%s.md' % version)
    if notes.is_file():
        found |= links_in(notes.read_text(encoding='utf-8'), 'docs/releases/notes')
    log = root / 'docs' / 'CHANGELOG.md'
    if log.is_file():
        found |= links_in(changelog_entry(log.read_text(encoding='utf-8'), version), 'docs')
    return sorted(p for p in found if (root / p).is_file() and p.startswith('docs/') and not p.startswith('docs/bugs/')
                  and not p.startswith('docs/releases/'))


def bump_only(diff_text, version):
    """True when a page's diff changes the last-updated line to this version and nothing else."""
    changed = [ln for ln in (diff_text or '').splitlines() if ln[:1] in ('+', '-') and not ln.startswith(('+++', '---'))]
    if not changed:
        return False
    stamps = [ln for ln in changed if UPDATED.match(ln[1:])]
    return bool(stamps) and len(stamps) == len(changed) and any(
        s.startswith('+') and ('v%s ' % version) in s for s in stamps)


def has_generated(text):
    return bool(GENERATED.search(text))


def run_registered(root, page):
    argv = REGISTRY[page]
    env = dict(os.environ, PYTHONPATH='tools:src', PYTHONDONTWRITEBYTECODE='1')
    r = subprocess.run([sys.executable] + argv, cwd=str(root), env=env, capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip().splitlines()[-1:] or ['']


def survey(root, diffs, version=None, runner=run_registered):
    """(pages, problems): every linked page as {page, bump_only, generated, checked}; the problems are the bump-only
    pages whose generated block differs from a fresh render."""
    root = Path(root)
    version = version or version_of(root)
    pages, problems = [], []
    for page in linked_pages(root, version):
        bump = bump_only((diffs or {}).get(page), version)
        gen = has_generated((root / page).read_text(encoding='utf-8'))
        row = {'page': page, 'bump_only': bump, 'generated': gen, 'checked': page in REGISTRY}
        if bump and gen and page in REGISTRY:
            ok, last = runner(root, page)
            row['fresh'] = ok
            if not ok:
                problems.append('%s: only its last-updated line changed in v%s and its generated block differs from a '
                                'fresh render (%s): run its generator and commit the result' % (page, version, last[0]))
        pages.append(row)
    return pages, problems


def report_lines(pages, version):
    out = ['Pages linked by the release notes and CHANGELOG entry of v%s: %d' % (version, len(pages))]
    for r in pages:
        note = []
        if r['bump_only']:
            note.append('ONLY THE LAST-UPDATED LINE CHANGED: the docs reviewer checks the content')
        if r['generated'] and not r['checked']:
            note.append('has a generated block, no fresh-render check registered')
        out.append('  %s%s' % (r['page'], ('  [' + '; '.join(note) + ']') if note else ''))
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in ('list', 'check'):
        print(__doc__)
        return 2
    version = version_of()
    try:
        diffs = json.loads(os.environ.get('PAGE_DIFFS') or '{}')
    except ValueError:
        print('RELEASE LINKED PAGES: PAGE_DIFFS is not JSON')
        return 1
    pages, problems = survey(ROOT, diffs, version)
    if argv[0] == 'list':
        print('\n'.join(report_lines(pages, version)))
        return 0
    for p in problems:
        print('RELEASE LINKED PAGES: ' + p)
    print('release linked pages check: %s (%d pages)' % ('FAIL' if problems else 'ok', len(pages)))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
