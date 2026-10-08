#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Bug register: docs/bugs/bugs.json is the source; docs/BUGS.md is generated.

Usage:
  bug_register.py render        rewrite the generated table in docs/BUGS.md
  bug_register.py check         validate bugs.json; fail if docs/BUGS.md is stale
  bug_register.py add ID --title T --found VERSION [--status TEXT] [--tag T...]
                                add an open bug (then write its report page)
  bug_register.py set ID [--state open|fixed|closed] [--fixed-in V]
                         [--status TEXT] [--owner-accepted V] [--tag T...]

Schema (docs/bugs/bugs.schema.json): a list of objects, one per bug, unique
"id"; "state" is open, fixed (a correction shipped in "fixed_in" with
verification) or closed (not a bug, duplicate or superseded; say why in
"status"). Rules and the report template: docs/bugs/README.md.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'docs' / 'bugs' / 'bugs.json'
REGISTER = ROOT / 'docs' / 'BUGS.md'
BEGIN = '<!-- BEGIN GENERATED BUG REGISTER: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->'
END = '<!-- END GENERATED BUG REGISTER -->'
ID_RE = re.compile(r'^(AW-\d{8}-\d{2}|[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-[0-9]{2,3}|[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-0[0-9])$')
FIELDS = {'id': str, 'title': str, 'state': str, 'fixed_in': (str, type(None)),
          'owner_accepted': (str, type(None)), 'status': str, 'report': (str, type(None))}
STATES = ('open', 'fixed', 'closed')
# Optional cross-cutting tags; each gets its own list below the register table.
TAGS = ('performance',)
VERSION_RE = re.compile(r'^v\d+\.\d+\.\d+(-[a-z]+\d*)?$')
# A development line such as v0.0.32-dev is a branch, not a shipped build (numbered -devN builds are).
DEV_LINE_RE = re.compile(r'^v\d+\.\d+\.\d+-dev$')


def load(path=DATA):
    return json.loads(path.read_text(encoding='utf-8'))


def save(bugs, path=DATA):
    path.write_text(json.dumps(bugs, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')


def validate(bugs):
    errors = []
    if not isinstance(bugs, list):
        return ['bugs.json must be a list']
    seen = set()
    for i, b in enumerate(bugs):
        where = b.get('id', '#%d' % i) if isinstance(b, dict) else '#%d' % i
        if not isinstance(b, dict):
            errors.append('%s: not an object' % where)
            continue
        if set(b) - {'tags'} != set(FIELDS):
            errors.append('%s: fields must be exactly %s (plus optional tags)' % (where, sorted(FIELDS)))
            continue
        tags = b.get('tags', [])
        if not isinstance(tags, list) or not tags and 'tags' in b or len(set(tags)) != len(tags) \
                or any(t not in TAGS for t in tags) or tags != sorted(tags):
            errors.append('%s: tags must be a sorted, non-empty list from %s' % (where, TAGS))
        for k, t in FIELDS.items():
            if not isinstance(b[k], t):
                errors.append('%s: %s has the wrong type' % (where, k))
        if not ID_RE.match(b['id']):
            errors.append('%s: ID must look like AREA-WHAT-NN' % where)
        if b['id'] in seen:
            errors.append('%s: duplicate ID' % where)
        seen.add(b['id'])
        if b['state'] not in STATES:
            errors.append('%s: state must be one of %s' % (where, STATES))
        if b['state'] == 'fixed' and not b['fixed_in']:
            errors.append('%s: a fixed bug needs fixed_in' % where)
        if b['state'] != 'fixed' and b['fixed_in']:
            errors.append('%s: only a fixed bug has fixed_in' % where)
        for k in ('fixed_in', 'owner_accepted'):
            if b[k] and not VERSION_RE.match(b[k]):
                errors.append('%s: %s must be a version like v0.0.30-rc1' % (where, k))
            elif b[k] and DEV_LINE_RE.match(b[k]):
                errors.append('%s: %s names a development line (%s), not a shipped build; keep the bug open '
                              'with "fixed in source" in status until a numbered build ships it' % (where, k, b[k]))
        if b['owner_accepted'] and b['state'] != 'fixed':
            errors.append('%s: owner_accepted needs a fixed bug' % where)
        if b['report'] and b['report'] != 'bugs/%s.md' % b['id']:
            errors.append('%s: report must be bugs/%s.md' % (where, b['id']))
        if b['report'] and not (REGISTER.parent / b['report']).is_file():
            errors.append('%s: report page missing' % where)
        if '|' in b['title'] + b['status'] or '\n' in b['title'] + b['status']:
            errors.append('%s: no | or line breaks in title/status' % where)
        if not b['status'].strip() or not b['title'].strip():
            errors.append('%s: title and status are required' % where)
    return errors


def table(bugs):
    out = ['| ID | Issue | State | Fixed in | Owner accepted | Status |', '| --- | --- | --- | --- | --- | --- |']
    order = {'open': 0, 'fixed': 1, 'closed': 2}
    for b in sorted(bugs, key=lambda b: (order[b['state']], b['id'])):
        ident = '[%s](%s)' % (b['id'], b['report']) if b['report'] else b['id']
        out.append('| %s | %s | %s | %s | %s | %s |' % (ident, b['title'], b['state'], b['fixed_in'] or '-',
                                                        b['owner_accepted'] or '-', b['status']))
    for tag in TAGS:
        tagged = [b for b in sorted(bugs, key=lambda b: (order[b['state']], b['id'])) if tag in b.get('tags', [])]
        if tagged:
            out += ['', '### Tagged %s' % tag, '']
            out += ['- %s: %s (%s)' % ('[%s](%s)' % (b['id'], b['report']) if b['report'] else b['id'],
                                         b['title'], b['state']) for b in tagged]
    return '\n'.join(out) + '\n'


def rendered(text, bugs):
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise SystemExit('docs/BUGS.md needs exactly one generated-register block')
    a = text.index(BEGIN) + len(BEGIN)
    b = text.index(END)
    counts = {s: sum(1 for x in bugs if x['state'] == s) for s in STATES}
    summary = '\n\n%d bugs: %d open, %d fixed, %d closed.\n\n' % (len(bugs), counts['open'], counts['fixed'], counts['closed'])
    return text[:a] + summary + table(bugs) + '\n' + text[b:]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('render'); sub.add_parser('check')
    a = sub.add_parser('add'); a.add_argument('id'); a.add_argument('--title', required=True)
    a.add_argument('--found', required=True); a.add_argument('--status')
    a.add_argument('--tag', action='append', choices=TAGS, default=[])
    s = sub.add_parser('set'); s.add_argument('id'); s.add_argument('--state', choices=STATES)
    s.add_argument('--fixed-in'); s.add_argument('--status'); s.add_argument('--owner-accepted')
    s.add_argument('--tag', action='append', choices=TAGS, default=[])
    args = p.parse_args(argv)
    bugs = load()
    if args.cmd == 'add':
        if any(b['id'] == args.id for b in bugs):
            raise SystemExit('ID exists: ' + args.id)
        page = 'bugs/%s.md' % args.id
        bugs.append({'id': args.id, 'title': args.title, 'state': 'open', 'fixed_in': None, 'owner_accepted': None,
                     'status': args.status or 'Reported in %s; cause unknown.' % args.found,
                     'report': page if (REGISTER.parent / page).is_file() else None})
        if args.tag:
            bugs[-1]['tags'] = sorted(set(args.tag))
    elif args.cmd == 'set':
        match = [b for b in bugs if b['id'] == args.id]
        if not match:
            raise SystemExit('unknown ID: ' + args.id)
        b = match[0]
        if args.state:
            b['state'] = args.state
            if args.state != 'fixed':
                b['fixed_in'] = None
        if args.fixed_in:
            b['fixed_in'] = args.fixed_in
        if args.status:
            b['status'] = args.status
        if args.owner_accepted:
            b['owner_accepted'] = args.owner_accepted
        if args.tag:
            b['tags'] = sorted(set(b.get('tags', [])) | set(args.tag))
        page = 'bugs/%s.md' % b['id']
        if (REGISTER.parent / page).is_file():
            b['report'] = page
    errors = validate(bugs)
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    text = REGISTER.read_text(encoding='utf-8')
    new = rendered(text, bugs)
    if args.cmd == 'check':
        if new != text:
            print('docs/BUGS.md is stale: run tools/bug_register.py render', file=sys.stderr)
            return 1
        print('bug register ok: %d bugs' % len(bugs))
        return 0
    if args.cmd in ('add', 'set'):
        save(bugs)
    REGISTER.write_text(new, encoding='utf-8', newline='\n')
    print('rendered %d bugs' % len(bugs))
    return 0


if __name__ == '__main__':
    sys.exit(main())
