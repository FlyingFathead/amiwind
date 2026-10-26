#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Search the bug register (docs/bugs/bugs.json and docs/bugs/archive/*.json), read only, standard library only.

    python3 tools/bug_lookup.py CHIM-CAVE                  ids containing a word, or bugs whose text has it
    python3 tools/bug_lookup.py non-convex collision       every word must match (id, title, where, status, family)
    python3 tools/bug_lookup.py --state open --family build-speed
    python3 tools/bug_lookup.py --found v0.0.48 --severity high
    python3 tools/bug_lookup.py --file tools/build_cache.py   bugs that name a repository file
    python3 tools/bug_lookup.py --persists                  bugs seen again in a later version
    python3 tools/bug_lookup.py ROOM-ACTORS-FLOATING-48 --page   print the report page too
    python3 tools/bug_lookup.py --json ...                  the matching records as JSON
    python3 tools/bug_lookup.py --like "Balmora chunks leave holes"   closest titles, open, fixed and closed

Before registering a bug, look it up: a problem seen again is marked PERSISTING on its existing entry, never added
twice; a fixed or closed bug seen again is a regression, reopened with tools/bug_register.py reopen
(REGISTER-REGRESSION-HANDLER-52). Added for v0.0.48 at the maintainer's request (24 October 2026); docs/bugs/README.md has the register's rules."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUGS = ROOT / 'docs' / 'bugs'
TEXT_FIELDS = ('id', 'title', 'where', 'status', 'family', 'chim', 'severity_reason')


def load(root=ROOT):
    """Every bug of the register: the live file first, then the archives (each record once, by id)."""
    bugs, seen = [], set()
    folder = Path(root) / 'docs' / 'bugs'
    for path in [folder / 'bugs.json'] + sorted((folder / 'archive').glob('*.json')):
        if not path.is_file():
            continue
        for bug in json.loads(path.read_text(encoding='utf-8')):
            if bug.get('id') not in seen:
                seen.add(bug.get('id'))
                bugs.append(dict(bug, archived=path.name != 'bugs.json'))
    return bugs


def text(bug):
    return ' '.join(str(bug.get(field) or '') for field in TEXT_FIELDS).casefold()


def matches(bug, args):
    if args.state and bug.get('state') != args.state:
        return False
    if args.family and bug.get('family') != args.family:
        return False
    if args.chim and bug.get('chim') != args.chim:
        return False
    if args.severity and bug.get('severity') != args.severity:
        return False
    if args.found and not str(bug.get('found_in') or '').startswith(args.found):
        return False
    if args.persists and len(bug.get('persists_in') or []) < 2 and 'PERSISTING' not in (bug.get('status') or ''):
        return False
    if args.file and args.file.casefold() not in text(bug):
        return False
    if not args.archived and bug.get('archived'):
        return False
    words = [word.casefold() for word in args.words]
    return all(word in bug.get('id', '').casefold() or word in text(bug) for word in words)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n', 1)[0])
    parser.add_argument('words', nargs='*', help='words that must all match the id or the text')
    parser.add_argument('--state', choices=('open', 'fixed', 'closed'))
    parser.add_argument('--family')
    parser.add_argument('--chim', help='CHIM part (streaming, builder, ...)')
    parser.add_argument('--severity', choices=('critical', 'high', 'medium', 'low'))
    parser.add_argument('--found', help='version prefix it was first found in, e.g. v0.0.48')
    parser.add_argument('--persists', action='store_true', help='seen again in a later version')
    parser.add_argument('--file', help='a repository path the bug names')
    parser.add_argument('--no-archived', dest='archived', action='store_false', help='live bugs only')
    parser.add_argument('--limit', type=int, default=40)
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--page', action='store_true', help='print each report page too')
    parser.add_argument('--like', metavar='TITLE', help='rank every bug (open, fixed, closed, archived) by how many '
                                                        'title words it shares with TITLE, closest first')
    parser.add_argument('--root', type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    found = [bug for bug in load(args.root) if matches(bug, args)]
    if args.like:
        # the register's own title score, the one bug_register.py add refuses on
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import bug_register
        found = [bug for _, bug in bug_register.closest(found, args.like, limit=args.limit,
                                                        states=bug_register.STATES)]
    shown = found[:args.limit]
    if args.json:
        print(json.dumps(shown, indent=2, ensure_ascii=False))
        return 0 if found else 1
    for bug in shown:
        title = bug.get('title') or ''
        back = ' [came back %d time%s]' % (len(bug['regressions']), '' if len(bug['regressions']) == 1 else 's') \
            if bug.get('regressions') else ''
        print('%-44s %-6s %-8s %-14s %s%s' % (bug.get('id'), bug.get('state'), bug.get('severity') or '-',
                                              bug.get('found_in') or '-',
                                              title if len(title) <= 90 else title[:87] + '...', back))
        page = Path(args.root) / 'docs' / 'bugs' / ('%s.md' % bug.get('id'))
        if args.page and page.is_file():
            print(page.read_text(encoding='utf-8'))
    gone = [bug['id'] for bug in shown[:3] if bug.get('state') in ('fixed', 'closed')]
    if gone and (args.like or len(shown) <= 3):
        print('fixed or closed: if one of these is seen again it is a regression, reopened, never added again: '
              'tools/bug_register.py reopen %s --version vX --at TIME' % gone[0], file=sys.stderr)
    more = len(found) - len(shown)
    print('%d bug%s%s' % (len(found), '' if len(found) == 1 else 's', ' (%d more: --limit)' % more if more > 0 else ''),
          file=sys.stderr)
    return 0 if found else 1


if __name__ == '__main__':
    sys.exit(main())
