#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The v0.0.55 docs/ reorganisation: move every per-version and one-off file out of the docs/ root.

Usage (inside a checkout, git on the path):
  docs_move.py plan      dry run: print every move, every file whose text changes and the counts; touches nothing
  docs_move.py apply     git mv every row of docs/history/MOVES.json, rewrite the links and paths, stage it all
  docs_move.py verify    check the staged change against HEAD: renames only, nothing deleted (run before the commit)

The rows live in docs/history/MOVES.json ("moves": old path -> new path; "superseded": old path -> the docs that
replace it). It is also the permanent record of where every file went.

Rule of the move (decided for the project, 28 October 2026): NOTHING IS DELETED. Every file is renamed with
`git mv`; this script never removes a file. `verify` refuses any path that leaves the tree without being a MOVES.json
row whose target is present, any added file outside the short list of new files, a changed file count, and an old
blob that is missing from the new tree unless the file's only change is its link text (moved files are checked to
differ ONLY inside link targets, plus the one "replaced by" line of a superseded doc, plus a final newline where an
old note had none: a changed file must be clean in full for the release preflight). It does not rely on git's
rename similarity: a note whose every paragraph links BUGS.md or bugs/ changes on many lines (../../ prefixes) and
falls under git's 50-90 % rename threshold; git's view is printed for the record.

What changes inside files:
  1. Markdown links `[x](target)`, reference definitions `[x]: target` and HTML src/href attributes in every
     tracked .md file: a relative target is resolved against the file's OLD folder, mapped through the moves and
     written relative to the file's NEW folder (anchors kept). Links that neither move nor point at a moved file are
     left byte for byte.
  2. Explicit path tokens `docs/<moved name>` in the other text files (tools, tests, README, JSON lists), except in
     frozen history (release notes, history, journals: links only) and the protected files below.
  3. Each superseded doc gets one added line under its "Last updated" line naming its replacement.
Never rewritten (byte-identical, asserted): the old PATCH-*.json whitespace baselines (their base_files name the
published trees' own paths), RECONCILE-BASES.json, WHITESPACE-BASELINE.json, docs/validation/, engine/aga/,
docs/aga/ and tests/resident_registry_budget.json (build and engine cache inputs). The register (docs/bugs/bugs.json)
and its frozen archive (docs/bugs/archive/*.json) hold Markdown links rendered into docs/BUGS.md: their link targets
are rewritten like a page's (the archive's words never change).
"""
import json
import posixpath
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path.cwd()
MOVES_FILE = 'docs/history/MOVES.json'
NEW_FILES = {
    'docs/README.md', 'docs/README.topics.json', 'docs/releases/README.md', 'docs/history/README.md',
    'docs/history/MOVES.json', 'tools/docs_index.py', 'tools/docs_move.py', 'tests/test_docs_layout.py',
    'tests/docs_broken_links_allowlist.json',
}
FROZEN_PREFIXES = ('docs/releases/', 'docs/history/', 'docs/journals/')
PROTECTED_PREFIXES = ('docs/validation/', 'engine/aga/', 'docs/aga/')
PROTECTED = {'docs/WHITESPACE-BASELINE.json', 'tests/resident_registry_budget.json'}
TEXT_SUFFIXES = {'.md', '.json', '.py', '.yml', '.yaml', '.txt', '.ps1', '.sh', '.cmd', '.c', '.h', '.js', '.html',
                 '.css', '.cfg', '.toml', '.in', '.ini', '.csv'}
MIN_SIMILARITY = 90
# JSON sources whose strings hold Markdown links, and the page their links are written relative to
LINK_BASE = {'docs/bugs/bugs.json': 'docs/BUGS.md'}


def link_base(path):
    """The page a JSON file's Markdown links are written relative to (the register and its frozen archive render
    into docs/BUGS.md), or None. The archive is frozen: only its link targets change, never a word."""
    if path in LINK_BASE:
        return LINK_BASE[path]
    if path.startswith('docs/bugs/archive/') and path.endswith('.json'):
        return 'docs/BUGS.md'
    return None

INLINE = re.compile(r'(\]\()(<?)([^)\s<>]+)(>?)((?:\s+"[^"]*")?\))')
REFDEF = re.compile(r'^( {0,3}\[[^\]\n]+\]:[ \t]*)(<?)(\S+?)(>?)([ \t]*(?:"[^"\n]*")?[ \t]*)$', re.M)
ATTR = re.compile(r'(\b(?:src|href)=")([^"]+)(")')
SKIP_SCHEME = re.compile(r'^(?:[a-zA-Z][a-zA-Z0-9+.-]*:|#|/|//)')


def git(*args, data=None):
    return subprocess.run(['git', *args], cwd=ROOT, input=data, stdout=subprocess.PIPE, check=True).stdout


def tracked():
    return [p for p in git('ls-files', '-z').decode('utf-8').split('\0') if p]


def load_moves():
    doc = json.loads((ROOT / MOVES_FILE).read_text(encoding='utf-8'))
    return doc['moves'], doc.get('superseded', {})


def is_protected(path, moves_inverse):
    old = moves_inverse.get(path, path)
    if old in PROTECTED or path in PROTECTED or old.startswith(PROTECTED_PREFIXES) or path.startswith(PROTECTED_PREFIXES):
        return True
    # every whitespace baseline and the reconcile record keep their bytes
    name = posixpath.basename(old)
    return (name.startswith('PATCH-') and name.endswith('.json')) or name == 'RECONCILE-BASES.json'


def rewrite_target(target, old_dir, new_dir, moves, moved_file):
    """The rewritten link target, or the target unchanged."""
    if SKIP_SCHEME.match(target):
        return target
    path, sep, frag = target.partition('#')
    if not path:
        return target
    plain = unquote(path)
    trailing = plain.endswith('/')
    old_abs = posixpath.normpath(posixpath.join(old_dir, plain))
    if old_abs.startswith('../') or old_abs == '..':
        return target
    new_abs = moves.get(old_abs, old_abs)
    if new_abs == old_abs and not moved_file:
        return target
    rel = posixpath.relpath(new_abs, new_dir or '.')
    if trailing and not rel.endswith('/'):
        rel += '/'
    if rel == posixpath.normpath(plain) and not moved_file:
        return target
    if '%' in path and plain != path:
        rel = quote(rel, safe="/#.-_~()!*'")
    return rel + sep + frag


def rewrite_links(text, old_path, new_path, moves):
    old_dir, new_dir = posixpath.dirname(old_path), posixpath.dirname(new_path)
    moved_file = old_path != new_path

    def inline(m):
        return m.group(1) + m.group(2) + rewrite_target(m.group(3), old_dir, new_dir, moves, moved_file) + m.group(4) + m.group(5)

    def refdef(m):
        return m.group(1) + m.group(2) + rewrite_target(m.group(3), old_dir, new_dir, moves, moved_file) + m.group(4) + m.group(5)

    def attr(m):
        return m.group(1) + rewrite_target(m.group(2), old_dir, new_dir, moves, moved_file) + m.group(3)

    text = INLINE.sub(inline, text)
    text = REFDEF.sub(refdef, text)
    return ATTR.sub(attr, text)


def token_pattern(moves):
    names = sorted((old[len('docs/'):] for old in moves), key=len, reverse=True)
    return re.compile(r'(?<![\w.-])docs/(%s)(?![\w-])' % '|'.join(re.escape(n) for n in names))


def rewrite_tokens(text, moves, pattern):
    return pattern.sub(lambda m: moves['docs/' + m.group(1)], text)


def superseded_line(new_path, replacements):
    links = ', '.join('[%s](%s)' % (posixpath.basename(r), posixpath.relpath(r, posixpath.dirname(new_path)))
                      for r in replacements)
    return '> Superseded and kept as history (moved here in v0.0.55): replaced by %s.' % links


LAST_UPDATED = re.compile(r'^_Last updated with AmiWind [^\n]*_\n', re.M)


def add_superseded(text, new_path, replacements):
    line = superseded_line(new_path, replacements)
    m = LAST_UPDATED.search(text)
    end = text.find('<!-- contents end -->\n')
    if end >= 0:
        # under the contents list, which stays where tools/doc_toc.py placed it
        at = end + len('<!-- contents end -->\n')
    elif m:
        at = m.end()
    else:
        at = text.index('\n') + 1   # under the title
    rest = text[at:]
    if rest.startswith('\n'):
        return text[:at] + '\n' + line + '\n' + rest
    return text[:at] + '\n' + line + '\n\n' + rest


def compute(moves, superseded):
    """(changes {new path: (old path, new text)}, notes) for every text file whose content changes."""
    files = tracked()
    present = set(files)
    for old, new in moves.items():
        if old not in present:
            raise SystemExit('MOVES row %s: not a tracked file' % old)
        if new in present:
            raise SystemExit('MOVES row %s: target %s exists' % (old, new))
    if len(set(moves.values())) != len(moves):
        raise SystemExit('MOVES: two rows share a target')
    for old in superseded:
        if old not in moves or not moves[old].startswith('docs/history/superseded/'):
            raise SystemExit('superseded row %s: not moved to docs/history/superseded/' % old)
        for r in superseded[old]:
            if r not in present and not (ROOT / r).is_dir():
                raise SystemExit('superseded row %s: replacement %s does not exist' % (old, r))
    inverse = {v: k for k, v in moves.items()}
    pattern = token_pattern(moves)
    changes = {}
    for old in files:
        new = moves.get(old, old)
        if posixpath.splitext(old)[1].lower() not in TEXT_SUFFIXES or is_protected(new, inverse):
            continue
        raw = (ROOT / old).read_bytes()
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError:
            continue
        out = text
        if old.endswith('.md'):
            out = rewrite_links(out, old, new, moves)
        elif link_base(old):        # Markdown held in JSON strings, rendered at that page
            out = rewrite_links(out, link_base(old), link_base(old), moves)
        if not new.startswith(FROZEN_PREFIXES + ('docs/bugs/archive/',)):
            out = rewrite_tokens(out, moves, pattern)
        if old in superseded:
            out = add_superseded(out, new, superseded[old])
        if out != text and old != new and not out.endswith('\n'):
            # a changed file is checked in full by the release preflight (raw bytes): an old note without a final
            # newline gets one with its link rewrite (two notes, RELEASE-v0.0.26 and -v0.0.29-dev4)
            out += '\n'
        if out != text:
            changes[new] = (old, out)
    return changes


def summary(moves, superseded, changes):
    by_dir = {}
    for new in moves.values():
        by_dir.setdefault(posixpath.dirname(new), 0)
        by_dir[posixpath.dirname(new)] += 1
    print('MOVES: %d files (renames only, nothing deleted)' % len(moves))
    for d in sorted(by_dir):
        print('  %4d -> %s/' % (by_dir[d], d))
    print('superseded docs (one added "replaced by" line each): %d' % len(superseded))
    moved_changed = sorted(n for n, (o, _) in changes.items() if o != n)
    other_changed = sorted(n for n, (o, _) in changes.items() if o == n)
    print('text changes: %d moved files (link targets), %d files that stay (links and paths)' % (
        len(moved_changed), len(other_changed)))
    for n in other_changed:
        print('  changes: %s' % n)


def cmd_plan():
    moves, superseded = load_moves()
    changes = compute(moves, superseded)
    for old in sorted(moves):
        print('MOVE %s -> %s' % (old, moves[old]))
    summary(moves, superseded, changes)
    if len(sys.argv) > 2:          # plan DIFF_FILE: the unified diff of every changed text, for review
        import difflib
        with open(sys.argv[2], 'w', encoding='utf-8', newline='\n') as out:
            for new, (old, text) in sorted(changes.items()):
                before = (ROOT / old).read_text(encoding='utf-8').splitlines(keepends=True)
                out.writelines(difflib.unified_diff(before, text.splitlines(keepends=True), old, new, n=0))
    print('DRY RUN: nothing was changed')
    return 0


def cmd_apply():
    staged = {p for p in git('diff', '--cached', '--name-only', '-z').decode().split('\0') if p}
    if staged - NEW_FILES:
        raise SystemExit('REFUSED: the index already holds staged changes (%s); apply starts from a clean index '
                         '(only the new files may be staged)' % sorted(staged - NEW_FILES)[:5])
    moves, superseded = load_moves()
    dirty = {p for p in git('diff', '--name-only', '-z').decode().split('\0') if p}
    touched = dirty & set(moves)
    if touched:
        raise SystemExit('REFUSED: moved files have unstaged edits: %s' % sorted(touched)[:5])
    changes = compute(moves, superseded)
    by_target = {}
    for old, new in sorted(moves.items()):
        by_target.setdefault(posixpath.dirname(new), []).append(old)
    for d, olds in sorted(by_target.items()):
        (ROOT / d).mkdir(parents=True, exist_ok=True)
        for i in range(0, len(olds), 100):
            # git mv only: this script never removes a file
            git('mv', '--', *olds[i:i + 100], d + '/')
    for new, (old, text) in sorted(changes.items()):
        with open(ROOT / new, 'w', encoding='utf-8', newline='') as handle:
            handle.write(text)
    names = sorted(changes)
    for i in range(0, len(names), 200):
        git('add', '--', *names[i:i + 200])
    summary(moves, superseded, changes)
    print('APPLIED: staged; run docs_move.py verify before the commit')
    return 0


LINK_TARGETS = [INLINE, REFDEF, ATTR]


def strip_links(text):
    text = INLINE.sub(lambda m: m.group(1) + '@' + m.group(5), text)
    text = REFDEF.sub(lambda m: m.group(1) + '@' + m.group(5), text)
    return ATTR.sub(lambda m: m.group(1) + '@' + m.group(3), text)


def cmd_verify():
    moves, superseded = load_moves()
    problems = []
    # Paths only (no rename detection): every path gone from the tree must be a MOVES.json source whose target is
    # present, and every new path a MOVES.json target or one of NEW_FILES. Content is proven below, blob by blob.
    rows = git('diff', '--cached', '--no-renames', '--name-status', '-z', 'HEAD').decode('utf-8').split('\0')
    rows = [r for r in rows if r]
    gone, added, modified = [], [], []
    for status, path in zip(rows[0::2], rows[1::2]):
        {'D': gone, 'A': added, 'M': modified}.get(status[0], problems).append(
            path if status[0] in 'DAM' else 'unexpected status %s %s' % (status, path))
    targets = set(moves.values())
    for d in gone:
        if d not in moves:
            problems.append('DELETED (not a move of MOVES.json): %s' % d)
    for old, new in moves.items():
        if old not in gone or new not in added:
            problems.append('move not staged as old path gone + new path present: %s -> %s' % (old, new))
    new_files = [a for a in added if a not in targets]
    for a in new_files:
        if a not in NEW_FILES:
            problems.append('added file outside the list of new files: %s' % a)
    head = {p for p in git('ls-tree', '-r', '--name-only', '-z', 'HEAD').decode().split('\0') if p}
    index = {p for p in git('ls-files', '-z').decode().split('\0') if p}
    if len(index) != len(head) + len(new_files):
        problems.append('file count: HEAD %d + new %d != index %d' % (len(head), len(new_files), len(index)))
    # git's own rename view (what a later merge sees): reported, the proof is the content check below
    sim = git('diff', '--cached', '-M50%', '-l100000', '--name-status', '-z', 'HEAD').decode('utf-8').split('\0')
    scores = [int(s[1:]) for s in sim if s[:1] == 'R' and s[1:].isdigit()]
    renamed = scores
    # every old blob is still there, or the file differs from its old self only inside link targets
    head_blobs = {}
    for row in git('ls-tree', '-r', '-z', 'HEAD').decode().split('\0'):
        if row:
            meta, name = row.split('\t', 1)
            head_blobs[name] = meta.split()[2]
    index_blobs = {}
    for row in git('ls-files', '-s', '-z').decode().split('\0'):
        if row:
            meta, name = row.split('\t', 1)
            index_blobs[name] = meta.split()[1]
    present = set(index_blobs.values())
    # modes: a moved file keeps its old mode, a new file is 100644 (the release kit refuses any other mode)
    head_modes = {}
    for row in git('ls-tree', '-r', '-z', 'HEAD').decode().split('\0'):
        if row:
            meta, name = row.split('\t', 1)
            head_modes[name] = meta.split()[0]
    old_of = {n: o for o, n in moves.items()}
    for row in git('ls-files', '-s', '-z').decode().split('\0'):
        if row:
            meta, name = row.split('\t', 1)
            want = head_modes.get(name) or head_modes.get(old_of.get(name, ''), '100644')
            if meta.split()[0] != want:
                problems.append('file mode %s, expected %s: %s' % (meta.split()[0], want, name))
    links_only = 0
    for old, new in moves.items():
        if head_blobs[old] in present and index_blobs.get(new) == head_blobs[old]:
            continue
        before = git('cat-file', 'blob', head_blobs[old]).decode('utf-8')
        after = git('cat-file', 'blob', index_blobs[new]).decode('utf-8')
        if old in superseded:
            before = add_superseded(before, new, superseded[old])   # the one added line is expected
        if is_protected(new, {v: k for k, v in moves.items()}):
            problems.append('protected file changed: %s' % new)
        elif strip_links(before) != strip_links(after) and strip_links(before) + '\n' != strip_links(after):
            problems.append('moved file changed outside link targets: %s' % new)
        else:
            links_only += 1
    for p in problems:
        print('FAIL ' + p)
    print('git rename view: %d of %d moves seen as renames at >= 50 %% similarity (%d at 100 %%, %d under %d %%: '
          'link-heavy notes)' % (len(renamed), len(moves), sum(1 for s in renamed if s == 100),
                                 sum(1 for s in renamed if s < MIN_SIMILARITY), MIN_SIMILARITY))
    print('verify: %d moves, %d new files, %d modified in place, %d moved files with link-only changes, %s' % (
        len(moves), len(new_files), len(modified), links_only, 'FAILED' if problems else 'nothing deleted: PASSED'))
    return 1 if problems else 0


def main(argv):
    if len(argv) not in (2, 3) or argv[1] not in ('plan', 'apply', 'verify') or (len(argv) == 3 and argv[1] != 'plan'):
        print(__doc__)
        return 2
    return {'plan': cmd_plan, 'apply': cmd_apply, 'verify': cmd_verify}[argv[1]]()


if __name__ == '__main__':
    sys.exit(main(sys.argv))
