# SPDX-License-Identifier: GPL-3.0-only
"""CHIM compatibility table: each CHIM version and its compatibility line (BUILD-CHIM-LABEL-IN-KEYS-48).

config/chim-compatibility.json lists every CHIM version with its line: the oldest CHIM version whose worlds and build
caches it reads unchanged, and a one-line reason. A version that only moves the label (the x.x.1 step of a final
release) keeps the line of the version before it; a version that changes what CHIM builds or reads starts a new line
(line = itself).

The stage and unit cache keys (tools/build_cache.py SourceIndex) take the line, not the label: the CHIM_VERSION file
counts in a key as the same file with its label replaced by the line, so a label-only bump keeps every key (a 0.2.2
key equals the 0.2.1 key of the same code) and a new line rebuilds. Receipts and records keep the real label.

    python3 tools/chim_compat.py check            table rules, CHIM_VERSION listed, the doc table current
    python3 tools/chim_compat.py render           write the table into docs/chim/README.md
    python3 tools/chim_compat.py line [VERSION]   the compatibility line of VERSION (default: CHIM_VERSION)
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLE = 'config/chim-compatibility.json'
LABEL = 'CHIM_VERSION'
DOC = 'docs/chim/README.md'
DOC_START = '<!-- chim-compatibility start (tools/chim_compat.py render) -->'
DOC_END = '<!-- chim-compatibility end -->'
VERSION_RE = re.compile(r'[0-9]+\.[0-9]+\.[0-9]+')


def _number(version):
    return tuple(int(part) for part in version.split('.'))


def load(root=ROOT):
    """The table's rows ({version, line, amiwind, reason}) in file order; None when the table does not exist."""
    path = Path(root) / TABLE
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding='utf-8'))['versions']


def label(root=ROOT):
    """The CHIM_VERSION label of ROOT."""
    return (Path(root) / LABEL).read_text(encoding='utf-8').strip()


def line_of(version, rows):
    """The compatibility line of VERSION; ValueError when the table does not list it (a bump adds its row)."""
    for row in rows:
        if row.get('version') == version:
            return row['line']
    raise ValueError('CHIM %s is not in %s: every CHIM_VERSION bump adds its row (version, line, reason)'
                     % (version, TABLE))


def reads(version, rows):
    """The CHIM versions whose worlds and caches VERSION reads unchanged: its line and every listed version of that line
    up to VERSION, oldest first."""
    line = line_of(version, rows)
    return sorted((row['version'] for row in rows
                   if row['line'] == line and _number(row['version']) <= _number(version)), key=_number)


def key_bytes(raw, rows):
    """The bytes of a CHIM_VERSION file (RAW) as the cache keys count them: the label replaced by its line. A label
    that is its own line gives RAW unchanged, so the keys of builds made before the table existed still match."""
    text = raw.decode('utf-8')
    version = text.strip()
    return text.replace(version, line_of(version, rows), 1).encode('utf-8')


def problems(root=ROOT):
    """Table rules: ascending unique versions, every line a listed version on its own line and not newer than its
    rows, a reason per row, CHIM_VERSION listed, and the doc table rendered from the table."""
    rows = load(root)
    if rows is None:
        return ['%s is missing' % TABLE]
    found, seen, previous = [], {}, None
    for row in rows:
        version, line = row.get('version'), row.get('line')
        if not (isinstance(version, str) and VERSION_RE.fullmatch(version)):
            found.append('row %r: version must look like 0.2.2' % (row,))
            continue
        if not (isinstance(line, str) and VERSION_RE.fullmatch(line)):
            found.append('CHIM %s: line must look like 0.2.1' % version)
            continue
        if version in seen:
            found.append('CHIM %s is listed twice' % version)
        if previous is not None and _number(version) <= _number(previous):
            found.append('CHIM %s comes after %s: rows go oldest first' % (version, previous))
        if _number(line) > _number(version):
            found.append('CHIM %s: line %s is newer than the version' % (version, line))
        if line != version and seen.get(line, {}).get('line') != line:
            found.append('CHIM %s: line %s must be an earlier row that starts its own line' % (version, line))
        if not str(row.get('reason') or '').strip() or '\n' in str(row.get('reason')):
            found.append('CHIM %s: one-line reason missing' % version)
        seen[version], previous = row, version
    current = label(root) if (Path(root) / LABEL).is_file() else None
    if current is not None and current not in seen:
        found.append('CHIM_VERSION %s is not in %s: add its row' % (current, TABLE))
    doc = Path(root) / DOC
    if doc.is_file() and current is not None and not found:
        text = doc.read_text(encoding='utf-8')
        if DOC_START not in text or DOC_END not in text:
            found.append('%s has no compatibility table markers' % DOC)
        elif text.split(DOC_START, 1)[1].split(DOC_END, 1)[0] != render(rows, current):
            found.append('%s compatibility table is stale: python3 tools/chim_compat.py render' % DOC)
    return found


def render(rows, current):
    """The doc block between the markers: the table and what CURRENT reads."""
    lines = ['', '| CHIM | Compatibility line | Shipped with | Reason |', '| --- | --- | --- | --- |']
    for row in rows:
        lines.append('| %s | %s | AmiWind %s | %s |' % (row['version'], row['line'], row.get('amiwind') or '-',
                                                       row['reason']))
    lines += ['', 'CHIM %s reads worlds and caches built by CHIM %s.' % (current, ', '.join(reads(current, rows))), '']
    return '\n'.join(lines)


def write_doc(root=ROOT):
    rows, current = load(root), label(root)
    doc = Path(root) / DOC
    text = doc.read_text(encoding='utf-8')
    head, rest = text.split(DOC_START, 1)
    tail = rest.split(DOC_END, 1)[1]
    doc.write_text(head + DOC_START + render(rows, current) + DOC_END + tail, encoding='utf-8', newline='\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('check')
    sub.add_parser('render')
    line = sub.add_parser('line')
    line.add_argument('version', nargs='?')
    args = parser.parse_args(argv)
    if args.action == 'check':
        found = problems()
        for problem in found:
            print(problem)
        print('CHIM compatibility table: %s' % ('ok' if not found else '%d problem(s)' % len(found)))
        return 1 if found else 0
    if args.action == 'render':
        write_doc()
        print('wrote %s' % DOC)
        return 0
    rows = load()
    version = args.version or label()
    print('%s line %s (reads %s)' % (version, line_of(version, rows), ', '.join(reads(version, rows))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
