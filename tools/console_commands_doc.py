#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Generate docs/AMIWIND_CONSOLE_COMMANDS.md from config/debug-commands.txt.

The catalogue is the file the engine itself reads (format AWDC1: one command per
line, GROUP|debug words|handler|help). Entries in a group that share a handler
are one command with aliases. Never edit the page by hand.

Usage:
  console_commands_doc.py render   rewrite docs/AMIWIND_CONSOLE_COMMANDS.md
  console_commands_doc.py check    fail if the page is out of date
  console_commands_doc.py sort     sort the catalogue: each group once, entries alphabetical
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / 'config' / 'debug-commands.txt'
PAGE = ROOT / 'docs' / 'AMIWIND_CONSOLE_COMMANDS.md'


def entries(text):
    lines = text.splitlines()
    if not lines or lines[0] != 'AWDC1':
        raise ValueError('debug-commands.txt must start with AWDC1')
    out = []
    for n, line in enumerate(lines[1:], 2):
        if not line or line.startswith('#'):
            continue
        parts = line.split('|')
        if len(parts) != 4 or not all(p.strip() for p in parts[:3]):
            raise ValueError('line %d: expected GROUP|words|handler|help' % n)
        out.append(tuple(p.strip() for p in parts))
    return out


def sorted_text(text):
    """Canonical catalogue: header and comment lines first, then each group once
    (in order of first appearance), entries alphabetical by their words."""
    lines = text.splitlines()
    head = [lines[0]] + [l for l in lines[1:] if not l or l.startswith('#')]
    rows = [l for l in lines[1:] if l and not l.startswith('#')]
    order = []
    for l in rows:
        g = l.split('|', 1)[0].strip()
        if g not in order: order.append(g)
    rows.sort(key=lambda l: (order.index(l.split('|', 1)[0].strip()), l.split('|')[1].strip().lower()))
    return '\n'.join([h for h in head if h] + rows) + '\n'


def registered_names(source_dir):
    """Command and setting names the engine registers (Cmd_AddCommand, cvars)."""
    import re
    names = set()
    for f in sorted(Path(source_dir).glob('*.c')):
        t = f.read_text(encoding='latin-1')
        names.update(re.findall(r'Cmd_AddCommand\s*\(\s*"([^"]+)"', t))
        names.update(re.findall(r'cvar_t\s+\w+\s*=\s*\{\s*"([^"]+)"', t))
        names.update(re.findall(r',\s*\w+\s*=\s*\{\s*"([^"]+)"', t))
    return names


def esc(text):
    return text.replace('|', '\\|')


STAMP_RE = re.compile(r'^_Last updated with AmiWind v[0-9][^\n]*\._$', re.M)


def page_stamp(page):
    """The page's own "_Last updated with AmiWind vX (date)._" line, or None."""
    match = STAMP_RE.search(page or '')
    return match.group(0) if match else None


def new_stamp(today=None):
    """A stamp for a page regenerated now: the source's VERSION and the host date (every public page carries one,
    a changed page gets a new one; maintainer 2026-10-18 / 2026-10-19)."""
    import datetime
    today = today or datetime.date.today()
    version = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
    return '_Last updated with AmiWind v%s (%d %s %d)._' % (version, today.day, today.strftime('%B'), today.year)


def render(text, stamp=None):
    groups = {}
    for group, words, handler, help_text in entries(text):
        cmds = groups.setdefault(group, {})
        cmd = cmds.setdefault(handler, {'words': [], 'help': help_text})
        cmd['words'].append(words)
    out = ['# AmiWind console commands', ''] + ([stamp, ''] if stamp else []) + [
           'Open the console with F10 or the backquote key and type',
           'a command, for example `dbg headlamp on`. This page is generated from',
           '`config/debug-commands.txt`, the catalogue the game itself reads, by',
           '`tools/console_commands_doc.py`; do not edit it by hand.', '',
           'At start-up, on every map load and with the `version` command the console shows the',
           'game and CHIM versions, the AmiQuake version and where help is (on a map load the',
           'AmiQuake line ends with `SERVER (<game code CRC>)`):', '',
           '```text', 'AmiWind v<version> / CHIM v<CHIM version>', 'AmiQuake: VERSION 1.09',
           'Type: "dbg help" for help.', '```', '']
    for group, cmds in groups.items():
        out += ['## ' + group.title(), '', '| Command | Also | Arguments and notes |', '| --- | --- | --- |']
        for cmd in cmds.values():
            first, *aliases = cmd['words']
            out.append('| `dbg %s` | %s | %s |' % (esc(first), ', '.join('`dbg %s`' % esc(a) for a in aliases) or '-',
                                                   esc(cmd['help']) or '-'))
        out.append('')
    return '\n'.join(out)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv not in (['render'], ['check'], ['sort']):
        print(__doc__, file=sys.stderr)
        return 2
    if argv == ['sort']:
        text = CATALOGUE.read_text(encoding='utf-8')
        CATALOGUE.write_bytes(sorted_text(text).encode('utf-8'))
        print('sorted', CATALOGUE.relative_to(ROOT))
        return 0
    catalogue = CATALOGUE.read_text(encoding='utf-8')
    current = PAGE.read_text(encoding='utf-8') if PAGE.is_file() else ''
    stamp = page_stamp(current)
    page = render(catalogue, stamp)
    if argv == ['render'] and current != page:
        page = render(catalogue, new_stamp())   # the commands changed (or no stamp yet): a new stamp
    if argv == ['check']:
        if stamp is None or current != page:
            print('docs/AMIWIND_CONSOLE_COMMANDS.md is stale or has no "Last updated" line: run '
                  'tools/console_commands_doc.py render', file=sys.stderr)
            return 1
        print('console command page ok')
        return 0
    PAGE.write_text(page, encoding='utf-8', newline='\n')
    print('wrote', PAGE.relative_to(ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
